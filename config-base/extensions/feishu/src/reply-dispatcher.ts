import {
  createReplyPrefixContext,
  createTypingCallbacks,
  logTypingFailure,
  type ClawdbotConfig,
  type ReplyPayload,
  type RuntimeEnv,
} from "openclaw/plugin-sdk/feishu";
import { resolveFeishuAccount } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { sendMediaFeishu } from "./media.js";
import type { MentionTarget } from "./mention.js";
import { buildMentionedCardContent } from "./mention.js";
import { getFeishuRuntime } from "./runtime.js";
import {
  resolveFeishuFormatDirective,
  sendMarkdownCardFeishu,
  sendMessageFeishu,
  shouldUseCardAuto,
} from "./send.js";
import { FeishuStreamingSession, mergeStreamingText } from "./streaming-card.js";
import { resolveReceiveIdType } from "./targets.js";
import { addTypingIndicator, removeTypingIndicator, type TypingIndicatorState } from "./typing.js";

function buildFirstPacketSummary(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  const sentence = normalized.split(/[。！？!?]/).find((seg) => seg.trim().length > 0) ?? normalized;
  const short = sentence.trim().slice(0, 80);
  return short.length === normalized.length ? short : `${short}…`;
}

/** Maximum age (ms) for a message to receive a typing indicator reaction.
 * Messages older than this are likely replays after context compaction (#30418). */
const TYPING_INDICATOR_MAX_AGE_MS = 2 * 60_000;
const MS_EPOCH_MIN = 1_000_000_000_000;

function normalizeEpochMs(timestamp: number | undefined): number | undefined {
  if (!Number.isFinite(timestamp) || timestamp === undefined || timestamp <= 0) {
    return undefined;
  }
  // Defensive normalization: some payloads use seconds, others milliseconds.
  // Values below 1e12 are treated as epoch-seconds.
  return timestamp < MS_EPOCH_MIN ? timestamp * 1000 : timestamp;
}

export type CreateFeishuReplyDispatcherParams = {
  cfg: ClawdbotConfig;
  agentId: string;
  runtime: RuntimeEnv;
  chatId: string;
  replyToMessageId?: string;
  /** When true, preserve typing indicator on reply target but send messages without reply metadata */
  skipReplyToInMessages?: boolean;
  replyInThread?: boolean;
  /** True when inbound message is already inside a thread/topic context */
  threadReply?: boolean;
  rootId?: string;
  mentionTargets?: MentionTarget[];
  accountId?: string;
  /** Epoch ms when the inbound message was created. Used to suppress typing
   *  indicators on old/replayed messages after context compaction (#30418). */
  messageCreateTimeMs?: number;
};

// Global tracker for active streaming sessions — used by bot.ts to skip standalone ACK
// messages when streaming card is already providing visual feedback to the user.
const _streamingActiveSessions = new Set<string>();
(globalThis as any).__ocFeishuStreamingActive = _streamingActiveSessions;

export function createFeishuReplyDispatcher(params: CreateFeishuReplyDispatcherParams) {
  const core = getFeishuRuntime();
  const {
    cfg,
    agentId,
    chatId,
    replyToMessageId,
    skipReplyToInMessages,
    replyInThread,
    threadReply,
    rootId,
    mentionTargets,
    accountId,
  } = params;
  const sendReplyToMessageId = skipReplyToInMessages ? undefined : replyToMessageId;
  const threadReplyMode = threadReply === true;
  const effectiveReplyInThread = threadReplyMode ? true : replyInThread;
  const account = resolveFeishuAccount({ cfg, accountId });
  const prefixContext = createReplyPrefixContext({ cfg, agentId });

  let typingState: TypingIndicatorState | null = null;
  const typingCallbacks = createTypingCallbacks({
    start: async () => {
      // Check if typing indicator is enabled (default: true)
      if (!(account.config.typingIndicator ?? true)) {
        return;
      }
      if (!replyToMessageId) {
        return;
      }
      // Skip typing indicator for old messages — likely replays after context
      // compaction that would flood users with stale notifications (#30418).
      const messageCreateTimeMs = normalizeEpochMs(params.messageCreateTimeMs);
      if (
        messageCreateTimeMs !== undefined &&
        Date.now() - messageCreateTimeMs > TYPING_INDICATOR_MAX_AGE_MS
      ) {
        return;
      }
      // Feishu reactions persist until explicitly removed, so skip keepalive
      // re-adds when a reaction already exists. Re-adding the same emoji
      // triggers a new push notification for every call (#28660).
      if (typingState?.reactionId) {
        return;
      }
      typingState = await addTypingIndicator({
        cfg,
        messageId: replyToMessageId,
        accountId,
        runtime: params.runtime,
      });
    },
    stop: async () => {
      if (!typingState) {
        return;
      }
      await removeTypingIndicator({ cfg, state: typingState, accountId, runtime: params.runtime });
      typingState = null;
    },
    onStartError: (err) =>
      logTypingFailure({
        log: (message) => params.runtime.log?.(message),
        channel: "feishu",
        action: "start",
        error: err,
      }),
    onStopError: (err) =>
      logTypingFailure({
        log: (message) => params.runtime.log?.(message),
        channel: "feishu",
        action: "stop",
        error: err,
      }),
  });

  const textChunkLimit = core.channel.text.resolveTextChunkLimit(cfg, "feishu", accountId, {
    fallbackLimit: 4000,
  });
  const chunkMode = core.channel.text.resolveChunkMode(cfg, "feishu");
  const tableMode = core.channel.text.resolveMarkdownTableMode({ cfg, channel: "feishu" });
  const renderMode = account.config?.renderMode ?? "auto";
  // Card streaming may miss thread affinity in topic contexts; use direct replies there.
  const streamingEnabled =
    !threadReplyMode && account.config?.streaming !== false && renderMode !== "raw";

  let streaming: FeishuStreamingSession | null = null;
  let streamText = "";
  let lastPartial = "";
  const deliveredFinalTexts = new Set<string>();
  let partialUpdateQueue: Promise<void> = Promise.resolve();
  let streamingStartPromise: Promise<void> | null = null;
  type StreamTextUpdateMode = "snapshot" | "delta";

  const queueStreamingUpdate = (
    nextText: string,
    options?: {
      dedupeWithLastPartial?: boolean;
      mode?: StreamTextUpdateMode;
    },
  ) => {
    if (!nextText) {
      return;
    }
    if (options?.dedupeWithLastPartial && nextText === lastPartial) {
      return;
    }
    if (options?.dedupeWithLastPartial) {
      lastPartial = nextText;
    }
    const mode = options?.mode ?? "snapshot";
    streamText =
      mode === "delta" ? `${streamText}${nextText}` : mergeStreamingText(streamText, nextText);
    partialUpdateQueue = partialUpdateQueue.then(async () => {
      if (streamingStartPromise) {
        await streamingStartPromise;
      }
      if (streaming?.isActive()) {
        await streaming.update(streamText);
      }
    });
  };

  const startStreaming = () => {
    if (!streamingEnabled || streamingStartPromise || streaming) {
      return;
    }
    streamingStartPromise = (async () => {
      const creds =
        account.appId && account.appSecret
          ? { appId: account.appId, appSecret: account.appSecret, domain: account.domain }
          : null;
      if (!creds) {
        return;
      }

      streaming = new FeishuStreamingSession(createFeishuClient(account), creds, (message) =>
        params.runtime.log?.(`feishu[${account.accountId}] ${message}`),
      );
      try {
        await streaming.start(chatId, resolveReceiveIdType(chatId), {
          replyToMessageId,
          replyInThread: effectiveReplyInThread,
          rootId,
        });
        _streamingActiveSessions.add(chatId);
      } catch (error) {
        params.runtime.error?.(`feishu: streaming start failed: ${String(error)}`);
        streaming = null;
      }
    })();
  };

  const closeStreaming = async () => {
    if (streamingStartPromise) {
      await streamingStartPromise;
    }
    await partialUpdateQueue;
    if (streaming?.isActive()) {
      let text = streamText;
      if (mentionTargets?.length) {
        text = buildMentionedCardContent(mentionTargets, text);
      }
      await streaming.close(text);
    }
    _streamingActiveSessions.delete(chatId);
    streaming = null;
    streamingStartPromise = null;
    streamText = "";
    lastPartial = "";
  };

  const { dispatcher, replyOptions, markDispatchIdle } =
    core.channel.reply.createReplyDispatcherWithTyping({
      responsePrefix: prefixContext.responsePrefix,
      responsePrefixContextProvider: prefixContext.responsePrefixContextProvider,
      humanDelay: core.channel.reply.resolveHumanDelayConfig(cfg, agentId),
      onReplyStart: () => {
        deliveredFinalTexts.clear();
        if (streamingEnabled && (renderMode === "card" || renderMode === "auto")) {
          startStreaming();
        }
        void typingCallbacks.onReplyStart?.();
      },
      deliver: async (payload: ReplyPayload, info) => {
        const normalizedText = resolveFeishuFormatDirective(payload.text ?? "");
        const text = normalizedText.text;
        const formatDirective = normalizedText.directive;
        const mediaList =
          payload.mediaUrls && payload.mediaUrls.length > 0
            ? payload.mediaUrls
            : payload.mediaUrl
              ? [payload.mediaUrl]
              : [];
        const hasText = Boolean(text.trim());
        const hasMedia = mediaList.length > 0;

        // Suppress system notification messages that add no user value
        const SYSTEM_NOISE_PATTERNS = [
          /^✅\s*New session started/,
          /^✅\s*Session resumed/,
          /^🔄\s*Session (reset|restarted)/,
          /^ℹ️?\s*(Model|Provider) switched/,
        ];
        if (hasText && !hasMedia && SYSTEM_NOISE_PATTERNS.some((p) => p.test(text.trim()))) {
          return;
        }

        // Enhanced dedup: exact match OR fuzzy substring overlap (catches prefix differences
        // between streaming card close text and standalone final text)
        const isFuzzyDuplicate = (candidate: string): boolean => {
          if (deliveredFinalTexts.has(candidate)) return true;
          const trimmed = candidate.trim();
          if (trimmed.length < 20) return false;
          for (const prev of deliveredFinalTexts) {
            // If either text contains 80%+ of the other, treat as duplicate
            if (prev.includes(trimmed) || trimmed.includes(prev)) return true;
            // Check suffix overlap: strip up to 40 chars of prefix and compare
            const shortCandidate = trimmed.length > 40 ? trimmed.slice(40) : trimmed;
            const shortPrev = prev.length > 40 ? prev.slice(40) : prev;
            if (shortCandidate.length > 20 && prev.includes(shortCandidate)) return true;
            if (shortPrev.length > 20 && trimmed.includes(shortPrev)) return true;
          }
          return false;
        };

        const skipTextForDuplicateFinal =
          info?.kind === "final" && hasText && isFuzzyDuplicate(text);
        const shouldDeliverText = hasText && !skipTextForDuplicateFinal;

        if (!shouldDeliverText && !hasMedia) {
          return;
        }

        if (shouldDeliverText) {
          const useCard =
            formatDirective === "card" ||
            (formatDirective !== "text" &&
              (renderMode === "card" || (renderMode === "auto" && shouldUseCardAuto(text))));
          const forceMsgType =
            formatDirective === "post"
              ? "post"
              : formatDirective === "text"
                ? "text"
                : undefined;

          if (info?.kind === "block") {
            // Drop internal block chunks unless we can safely consume them as
            // streaming-card fallback content.
            if (!(streamingEnabled && useCard)) {
              return;
            }
            startStreaming();
            if (streamingStartPromise) {
              await streamingStartPromise;
            }
          }

          if (info?.kind === "final" && streamingEnabled && useCard) {
            startStreaming();
            if (streamingStartPromise) {
              await streamingStartPromise;
            }
          }

          if (streaming?.isActive()) {
            if (info?.kind === "block") {
              // Some runtimes emit block payloads without onPartial/final callbacks.
              // Mirror block text into streamText so onIdle close still sends content.
              queueStreamingUpdate(text, { mode: "delta" });
            }
            if (info?.kind === "final") {
              streamText = mergeStreamingText(streamText, text);
              await closeStreaming();
              deliveredFinalTexts.add(text);
            }
            // Send media even when streaming handled the text
            if (hasMedia) {
              for (const mediaUrl of mediaList) {
                await sendMediaFeishu({
                  cfg,
                  to: chatId,
                  mediaUrl,
                  replyToMessageId: sendReplyToMessageId,
                  replyInThread: effectiveReplyInThread,
                  accountId,
                });
              }
            }
            return;
          }

          let first = true;
          if (info?.kind === "final" && text.length > 220) {
            const summary = buildFirstPacketSummary(text);
            if (summary) {
              await sendMessageFeishu({
                cfg,
                to: chatId,
                text: `【先给结论】${summary}`,
                replyToMessageId: sendReplyToMessageId,
                replyInThread: effectiveReplyInThread,
                mentions: mentionTargets,
                accountId,
                forceMsgType: "text",
              });
              first = false;
            }
          }
          if (useCard) {
            for (const chunk of core.channel.text.chunkTextWithMode(
              text,
              textChunkLimit,
              chunkMode,
            )) {
              try {
                await sendMarkdownCardFeishu({
                  cfg,
                  to: chatId,
                  text: chunk,
                  replyToMessageId: sendReplyToMessageId,
                  replyInThread: effectiveReplyInThread,
                  mentions: first ? mentionTargets : undefined,
                  accountId,
                });
              } catch (cardErr) {
                params.runtime.log?.(
                  `feishu[${account.accountId}] markdown card failed; fallback to text: ${String(cardErr)}`,
                );
                const fallbackText = core.channel.text.convertMarkdownTables(chunk, tableMode);
                await sendMessageFeishu({
                  cfg,
                  to: chatId,
                  text: fallbackText,
                  replyToMessageId: sendReplyToMessageId,
                  replyInThread: effectiveReplyInThread,
                  mentions: first ? mentionTargets : undefined,
                  accountId,
                  forceMsgType,
                });
              }
              first = false;
            }
            if (info?.kind === "final") {
              deliveredFinalTexts.add(text);
            }
          } else {
            const converted = core.channel.text.convertMarkdownTables(text, tableMode);
            for (const chunk of core.channel.text.chunkTextWithMode(
              converted,
              textChunkLimit,
              chunkMode,
            )) {
              await sendMessageFeishu({
                cfg,
                to: chatId,
                text: chunk,
                replyToMessageId: sendReplyToMessageId,
                replyInThread: effectiveReplyInThread,
                mentions: first ? mentionTargets : undefined,
                accountId,
                forceMsgType,
              });
              first = false;
            }
            if (info?.kind === "final") {
              deliveredFinalTexts.add(text);
            }
          }
        }

        if (hasMedia) {
          for (const mediaUrl of mediaList) {
            await sendMediaFeishu({
              cfg,
              to: chatId,
              mediaUrl,
              replyToMessageId: sendReplyToMessageId,
              replyInThread: effectiveReplyInThread,
              accountId,
            });
          }
        }
      },
      onError: async (error, info) => {
        params.runtime.error?.(
          `feishu[${account.accountId}] ${info.kind} reply failed: ${String(error)}`,
        );
        await closeStreaming();
        typingCallbacks.onIdle?.();
      },
      onIdle: async () => {
        await closeStreaming();
        typingCallbacks.onIdle?.();
      },
      onCleanup: () => {
        typingCallbacks.onCleanup?.();
      },
    });

  return {
    dispatcher,
    replyOptions: {
      ...replyOptions,
      onModelSelected: prefixContext.onModelSelected,
      disableBlockStreaming: true,
      onPartialReply: streamingEnabled
        ? (payload: ReplyPayload) => {
            if (!payload.text) {
              return;
            }
            queueStreamingUpdate(payload.text, {
              dedupeWithLastPartial: true,
              mode: "snapshot",
            });
          }
        : undefined,
    },
    markDispatchIdle,
  };
}
