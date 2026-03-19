import type { ClawdbotConfig, RuntimeEnv } from "openclaw/plugin-sdk";
import fs from "node:fs/promises";
import {
  buildAgentMediaPayload,
  buildPendingHistoryContextFromMap,
  clearHistoryEntriesIfEnabled,
  DEFAULT_GROUP_HISTORY_LIMIT,
  type HistoryEntry,
  recordPendingHistoryEntryIfEnabled,
  resolveOpenProviderRuntimeGroupPolicy,
  resolveDefaultGroupPolicy,
  warnMissingProviderGroupPolicyFallbackOnce,
} from "openclaw/plugin-sdk";
import { resolveFeishuAccount } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { tryRecordMessagePersistent } from "./dedup.js";
import { maybeCreateDynamicAgent } from "./dynamic-agent.js";
import { normalizeFeishuExternalKey } from "./external-keys.js";
import { downloadMessageResourceFeishu, sendMediaFeishu } from "./media.js";
import {
  escapeRegExp,
  extractMentionTargets,
  extractMessageBody,
  isMentionForwardRequest,
} from "./mention.js";
import {
  resolveFeishuGroupConfig,
  resolveFeishuReplyPolicy,
  resolveFeishuAllowlistMatch,
  isFeishuGroupAllowed,
} from "./policy.js";
import { createFeishuReplyDispatcher } from "./reply-dispatcher.js";
import { getFeishuRuntime } from "./runtime.js";
import { getMessageFeishu, sendMessageFeishu, deleteMessageFeishu } from "./send.js";
import {
  executeCommerceShopperCommand,
  isCommerceShopperCommand,
} from "./commerce-travel-shopper-bridge.js";
import type { FeishuConfig, FeishuMessageContext, FeishuMediaInfo, ResolvedFeishuAccount } from "./types.js";
import type { DynamicAgentCreationConfig } from "./types.js";

// --- Permission error extraction ---
// Extract permission grant URL from Feishu API error response.
type PermissionError = {
  code: number;
  message: string;
  grantUrl?: string;
};

function extractPermissionError(err: unknown): PermissionError | null {
  if (!err || typeof err !== "object") return null;

  // Axios error structure: err.response.data contains the Feishu error
  const axiosErr = err as { response?: { data?: unknown } };
  const data = axiosErr.response?.data;
  if (!data || typeof data !== "object") return null;

  const feishuErr = data as {
    code?: number;
    msg?: string;
    error?: { permission_violations?: Array<{ uri?: string }> };
  };

  // Feishu permission error code: 99991672
  if (feishuErr.code !== 99991672) return null;

  // Extract the grant URL from the error message (contains the direct link)
  const msg = feishuErr.msg ?? "";
  const urlMatch = msg.match(/https:\/\/[^\s,]+\/app\/[^\s,]+/);
  const grantUrl = urlMatch?.[0];

  return {
    code: feishuErr.code,
    message: msg,
    grantUrl,
  };
}

// --- Sender name resolution (so the agent can distinguish who is speaking in group chats) ---
// Cache display names by open_id to avoid an API call on every message.
const SENDER_NAME_TTL_MS = 2 * 60 * 60 * 1000;
const senderNameCache = new Map<string, { name: string; expireAt: number }>();

// Cache permission errors to avoid spamming the user with repeated notifications.
// Key: appId or "default", Value: timestamp of last notification
const permissionErrorNotifiedAt = new Map<string, number>();
const PERMISSION_ERROR_COOLDOWN_MS = 5 * 60 * 1000; // 5 minutes
const DEFAULT_RESPONSE_WATCHDOG_SEC = 30;
const SLOW_DISPATCH_WARN_MS = 6_000;
const SLOW_LANE_WAIT_WARN_MS = 2_000;
const QUEUE_NOTICE_COOLDOWN_MS = 60_000;
const SESSION_LATENCY_ESTIMATE_DEFAULT_MS = 8_000;
const SESSION_LATENCY_ESTIMATE_MIN_MS = 2_000;
const SESSION_LATENCY_ESTIMATE_MAX_MS = 90_000;
const SESSION_LATENCY_ESTIMATE_ALPHA = 0.4;
const DM_BURST_WINDOW_MS = 2_500;
const GROUP_HEAVY_THROTTLE_MS = 4_000;
const GROUP_HEAVY_BODY_LEN = 200;
const LANE_DISPATCH_TIMEOUT_MS = 90_000; // 1.5 min hard cap per dispatch to prevent lane deadlock
const MAX_TRACKED_SESSIONS = 500;
const DM_ACK_DELAY_MS = 2_000;
const LIGHTWEIGHT_QUERY_MAX_LEN = 15;
const LIGHTWEIGHT_QUERY_PATTERNS = [
  /^(hi|hello|hey|你好|嗨|在吗|在不在|ok|好的|谢谢|感谢|收到|嗯|哦|行|对|是的|没事|好|拜拜|再见|晚安|早安|早上好|下午好|晚上好)[\s!！。.？?]*$/i,
];

// Serialize dispatches per session to avoid stacked in-flight runs in the same chat/session.
type DispatchLaneTask = {
  run: () => Promise<unknown>;
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
  enqueuedAt: number;
};
type DispatchLaneState = {
  active: number;
  queue: DispatchLaneTask[];
  lastTouchedAt: number;
};
const sessionDispatchLanes = new Map<string, DispatchLaneState>();
const queueNoticeNotifiedAt = new Map<string, number>();
const dmSessionLatencyEstimateMs = new Map<string, number>();
const groupSessionLatencyEstimateMs = new Map<string, number>();
const dmBurstMergedBodyBySession = new Map<string, { lastAt: number; mergedBody: string; count: number }>();
const groupHeavyThrottleAtBySession = new Map<string, number>();

// If a run exits without an immediate final reply, send a delayed progress notice once.
const pendingFinalNoticeTimers = new Map<string, NodeJS.Timeout>();
const pendingFinalNoticeCounts = new Map<string, number>();

// Periodic cleanup of stale Map entries to prevent unbounded memory growth.
const CACHE_CLEANUP_INTERVAL_MS = 10 * 60_000; // 10 minutes
const STALE_ENTRY_AGE_MS = 30 * 60_000; // 30 minutes
setInterval(() => {
  const now = Date.now();
  // senderNameCache: evict expired entries
  for (const [key, val] of senderNameCache) {
    if (val.expireAt <= now) senderNameCache.delete(key);
  }
  // permissionErrorNotifiedAt: evict entries older than cooldown
  for (const [key, ts] of permissionErrorNotifiedAt) {
    if (now - ts > PERMISSION_ERROR_COOLDOWN_MS * 2) permissionErrorNotifiedAt.delete(key);
  }
  // dmBurstMergedBodyBySession: evict entries older than stale threshold
  for (const [key, val] of dmBurstMergedBodyBySession) {
    if (now - val.lastAt > STALE_ENTRY_AGE_MS) dmBurstMergedBodyBySession.delete(key);
  }
  // groupHeavyThrottleAtBySession: evict stale throttle timestamps
  for (const [key, ts] of groupHeavyThrottleAtBySession) {
    if (now - ts > STALE_ENTRY_AGE_MS) groupHeavyThrottleAtBySession.delete(key);
  }
  // Clean stale lane states.
  for (const [key, lane] of sessionDispatchLanes) {
    if (lane.active === 0 && lane.queue.length === 0 && now - lane.lastTouchedAt > STALE_ENTRY_AGE_MS) {
      sessionDispatchLanes.delete(key);
      queueNoticeNotifiedAt.delete(key);
    }
  }

  // Cap map sizes (keep insertion-order oldest dropped first).
  const trimMap = <K, V>(map: Map<K, V>, maxSize: number) => {
    if (map.size <= maxSize) return;
    const excess = map.size - maxSize;
    let removed = 0;
    for (const key of map.keys()) {
      if (removed >= excess) break;
      map.delete(key);
      removed += 1;
    }
  };
  trimMap(dmSessionLatencyEstimateMs, 200);
  trimMap(groupSessionLatencyEstimateMs, 200);
  trimMap(queueNoticeNotifiedAt, MAX_TRACKED_SESSIONS);
  trimMap(pendingFinalNoticeCounts, MAX_TRACKED_SESSIONS);
  if (sessionDispatchLanes.size > MAX_TRACKED_SESSIONS) {
    for (const [key, lane] of sessionDispatchLanes) {
      if (sessionDispatchLanes.size <= MAX_TRACKED_SESSIONS) break;
      if (lane.active === 0 && lane.queue.length === 0) {
        sessionDispatchLanes.delete(key);
      }
    }
  }
}, CACHE_CLEANUP_INTERVAL_MS).unref();

type SenderNameResult = {
  name?: string;
  permissionError?: PermissionError;
};

function getCachedSenderName(senderOpenId: string): string | undefined {
  const normalized = senderOpenId.trim();
  if (!normalized) {
    return undefined;
  }
  const cached = senderNameCache.get(normalized);
  if (!cached) {
    return undefined;
  }
  if (cached.expireAt <= Date.now()) {
    senderNameCache.delete(normalized);
    return undefined;
  }
  return cached.name;
}

async function refreshFeishuSenderName(params: {
  account: ResolvedFeishuAccount;
  senderOpenId: string;
  log: (...args: any[]) => void;
}): Promise<SenderNameResult> {
  const { account, senderOpenId, log } = params;
  if (!account.configured) return {};
  if (!senderOpenId) return {};

  const cachedName = getCachedSenderName(senderOpenId);
  if (cachedName) {
    return { name: cachedName };
  }
  const now = Date.now();

  try {
    const client = createFeishuClient(account);

    // contact/v3/users/:user_id?user_id_type=open_id
    const res: any = await client.contact.user.get({
      path: { user_id: senderOpenId },
      params: { user_id_type: "open_id" },
    });

    const name: string | undefined =
      res?.data?.user?.name ||
      res?.data?.user?.display_name ||
      res?.data?.user?.nickname ||
      res?.data?.user?.en_name;

    if (name && typeof name === "string") {
      senderNameCache.set(senderOpenId, { name, expireAt: now + SENDER_NAME_TTL_MS });
      return { name };
    }

    return {};
  } catch (err) {
    // Check if this is a permission error
    const permErr = extractPermissionError(err);
    if (permErr) {
      log(`feishu: permission error resolving sender name: code=${permErr.code}`);
      return { permissionError: permErr };
    }

    // Best-effort. Don't fail message handling if name lookup fails.
    log(`feishu: failed to resolve sender name for ${senderOpenId}: ${String(err)}`);
    return {};
  }
}

export type FeishuMessageEvent = {
  sender: {
    sender_id: {
      open_id?: string;
      user_id?: string;
      union_id?: string;
    };
    sender_type?: string;
    tenant_key?: string;
  };
  message: {
    message_id: string;
    root_id?: string;
    parent_id?: string;
    chat_id: string;
    chat_type: "p2p" | "group";
    message_type: string;
    content: string;
    mentions?: Array<{
      key: string;
      id: {
        open_id?: string;
        user_id?: string;
        union_id?: string;
      };
      name: string;
      tenant_key?: string;
    }>;
  };
};

export type FeishuBotAddedEvent = {
  chat_id: string;
  operator_id: {
    open_id?: string;
    user_id?: string;
    union_id?: string;
  };
  external: boolean;
  operator_tenant_key?: string;
};

function parseMessageContent(content: string, messageType: string): string {
  try {
    const parsed = JSON.parse(content);
    if (messageType === "text") {
      return parsed.text || "";
    }
    if (messageType === "post") {
      // Extract text content from rich text post
      const { textContent } = parsePostContent(content);
      return textContent;
    }
    return content;
  } catch {
    return content;
  }
}

function checkBotMentioned(event: FeishuMessageEvent, botOpenId?: string): boolean {
  if (!botOpenId) return false;
  const mentions = event.message.mentions ?? [];
  if (mentions.length > 0) {
    return mentions.some((m) => m.id.open_id === botOpenId);
  }
  // Post (rich text) messages may have empty message.mentions when they contain docs/paste
  if (event.message.message_type === "post") {
    const { mentionedOpenIds } = parsePostContent(event.message.content);
    return mentionedOpenIds.some((id) => id === botOpenId);
  }
  return false;
}

export function stripBotMention(
  text: string,
  mentions?: FeishuMessageEvent["message"]["mentions"],
): string {
  if (!mentions || mentions.length === 0) return text;
  let result = text;
  for (const mention of mentions) {
    result = result.replace(new RegExp(`@${escapeRegExp(mention.name)}\\s*`, "g"), "");
    result = result.replace(new RegExp(escapeRegExp(mention.key), "g"), "");
  }
  return result.trim();
}

function readResponseWatchdogSeconds(feishuCfg: FeishuConfig | undefined): number {
  const raw = Number(feishuCfg?.responseWatchdogSec ?? DEFAULT_RESPONSE_WATCHDOG_SEC);
  if (!Number.isFinite(raw)) {
    return DEFAULT_RESPONSE_WATCHDOG_SEC;
  }
  return Math.max(10, Math.min(300, Math.floor(raw)));
}

function clearPendingFinalNotice(sessionKey: string): void {
  const timer = pendingFinalNoticeTimers.get(sessionKey);
  if (timer) {
    clearTimeout(timer);
    pendingFinalNoticeTimers.delete(sessionKey);
  }
  pendingFinalNoticeCounts.delete(sessionKey);
}

function schedulePendingFinalNotice(params: {
  sessionKey: string;
  delayMs: number;
  log: (...args: any[]) => void;
  sendNotice: () => Promise<void>;
}): void {
  const { sessionKey, delayMs, log, sendNotice } = params;
  if (pendingFinalNoticeTimers.has(sessionKey)) {
    return;
  }
  const timer = setTimeout(() => {
    pendingFinalNoticeTimers.delete(sessionKey);
    const count = Number(pendingFinalNoticeCounts.get(sessionKey) || 0) + 1;
    pendingFinalNoticeCounts.set(sessionKey, count);
    void sendNotice().catch((err) => {
      log(`feishu: delayed progress notice failed (session=${sessionKey}): ${String(err)}`);
    });
  }, delayMs);
  pendingFinalNoticeTimers.set(sessionKey, timer);
}

function resolveNextPendingNoticeDelayMs(currentCount: number, firstDelayMs: number): number {
  if (currentCount <= 1) {
    return Math.min(firstDelayMs * 3, 120_000);
  }
  if (currentCount === 2) {
    return Math.min(firstDelayMs * 8, 240_000);
  }
  return 0;
}

async function runInSessionDispatchLane<T>(
  sessionKey: string,
  task: () => Promise<T>,
  maxConcurrency = 1,
): Promise<T> {
  const normalizedConcurrency = Math.max(1, Math.min(8, Math.floor(maxConcurrency || 1)));
  let lane = sessionDispatchLanes.get(sessionKey);
  if (!lane) {
    lane = { active: 0, queue: [], lastTouchedAt: Date.now() };
    sessionDispatchLanes.set(sessionKey, lane);
  }
  lane.lastTouchedAt = Date.now();

  return await new Promise<T>((resolve, reject) => {
    const dispatchTask: DispatchLaneTask = {
      enqueuedAt: Date.now(),
      resolve: (value) => resolve(value as T),
      reject,
      run: async () => {
        return Promise.race([
          task(),
          new Promise<never>((_, timeoutReject) =>
            setTimeout(
              () =>
                timeoutReject(
                  new Error(`Lane dispatch timeout after ${LANE_DISPATCH_TIMEOUT_MS}ms`),
                ),
              LANE_DISPATCH_TIMEOUT_MS,
            ),
          ),
        ]);
      },
    };
    lane?.queue.push(dispatchTask);

    const pump = () => {
      const currentLane = sessionDispatchLanes.get(sessionKey);
      if (!currentLane) {
        return;
      }
      while (
        currentLane.active < normalizedConcurrency &&
        currentLane.queue.length > 0
      ) {
        const nextTask = currentLane.queue.shift();
        if (!nextTask) {
          break;
        }
        currentLane.active += 1;
        currentLane.lastTouchedAt = Date.now();
        void nextTask
          .run()
          .then((value) => {
            nextTask.resolve(value);
          })
          .catch((error) => {
            nextTask.reject(error);
          })
          .finally(() => {
            const latestLane = sessionDispatchLanes.get(sessionKey);
            if (!latestLane) {
              return;
            }
            latestLane.active = Math.max(0, latestLane.active - 1);
            latestLane.lastTouchedAt = Date.now();
            if (latestLane.active === 0 && latestLane.queue.length === 0) {
              sessionDispatchLanes.delete(sessionKey);
              queueNoticeNotifiedAt.delete(sessionKey);
            } else {
              pump();
            }
          });
      }
    };

    pump();
  });
}

function hasPendingLaneWork(sessionKey: string): boolean {
  const lane = sessionDispatchLanes.get(sessionKey);
  if (!lane) {
    return false;
  }
  return lane.active > 0 || lane.queue.length > 0;
}

function getLaneQueueDepth(sessionKey: string): number {
  const lane = sessionDispatchLanes.get(sessionKey);
  if (!lane) {
    return 0;
  }
  return lane.active + lane.queue.length;
}

function maybeRefreshFeishuSenderNameInBackground(params: {
  account: ResolvedFeishuAccount;
  senderOpenId: string;
  log: (...args: any[]) => void;
  onPermissionError: (permissionError: PermissionError) => void;
}): void {
  const { account, senderOpenId, log, onPermissionError } = params;
  if (!account.config.resolveSenderNames || !senderOpenId) {
    return;
  }
  void refreshFeishuSenderName({ account, senderOpenId, log })
    .then((result) => {
      if (result.permissionError) {
        onPermissionError(result.permissionError);
      }
    })
    .catch((err) => {
      log(`feishu: background sender name refresh failed: ${String(err)}`);
    });
}

function shouldSendQueueNotice(sessionKey: string, now: number): boolean {
  const lastNotifiedAt = Number(queueNoticeNotifiedAt.get(sessionKey) || 0);
  if (now - lastNotifiedAt < QUEUE_NOTICE_COOLDOWN_MS) {
    return false;
  }
  queueNoticeNotifiedAt.set(sessionKey, now);
  return true;
}

function formatEtaSeconds(ms: number): number {
  return Math.max(2, Math.ceil(ms / 1000));
}

function estimateSessionWaitMs(sessionKey: string, queueDepth: number, isGroup: boolean): number {
  const table = isGroup ? groupSessionLatencyEstimateMs : dmSessionLatencyEstimateMs;
  const base = Number(table.get(sessionKey) || SESSION_LATENCY_ESTIMATE_DEFAULT_MS);
  const depth = Math.max(1, queueDepth);
  return Math.max(
    SESSION_LATENCY_ESTIMATE_MIN_MS,
    Math.min(SESSION_LATENCY_ESTIMATE_MAX_MS, base * depth),
  );
}

function updateSessionLatencyEstimate(sessionKey: string, latestLatencyMs: number, isGroup: boolean): void {
  if (!Number.isFinite(latestLatencyMs) || latestLatencyMs <= 0) {
    return;
  }
  const bounded = Math.max(
    SESSION_LATENCY_ESTIMATE_MIN_MS,
    Math.min(SESSION_LATENCY_ESTIMATE_MAX_MS, Math.floor(latestLatencyMs)),
  );
  const table = isGroup ? groupSessionLatencyEstimateMs : dmSessionLatencyEstimateMs;
  const existing = Number(table.get(sessionKey) || 0);
  const next = existing > 0
    ? Math.round((existing * (1 - SESSION_LATENCY_ESTIMATE_ALPHA)) + (bounded * SESSION_LATENCY_ESTIMATE_ALPHA))
    : bounded;
  table.set(sessionKey, next);
}

function mergeDmBurstBody(sessionKey: string, body: string, now: number): {
  mergedBody: string;
  burstCount: number;
} {
  const normalized = body.trim();
  const existing = dmBurstMergedBodyBySession.get(sessionKey);
  if (!existing || now - existing.lastAt > DM_BURST_WINDOW_MS) {
    dmBurstMergedBodyBySession.set(sessionKey, { lastAt: now, mergedBody: normalized, count: 1 });
    return { mergedBody: normalized, burstCount: 1 };
  }

  const nextCount = existing.count + 1;
  const mergedBody = `${existing.mergedBody}\n\n[用户连续补充#${nextCount}]\n${normalized}`;
  dmBurstMergedBodyBySession.set(sessionKey, { lastAt: now, mergedBody, count: nextCount });
  return { mergedBody, burstCount: nextCount };
}

function shouldThrottleGroupHeavyMessage(params: {
  sessionKey: string;
  body: string;
  now: number;
  hadPendingLane: boolean;
}): boolean {
  const { sessionKey, body, now, hadPendingLane } = params;
  if (!hadPendingLane || body.trim().length < GROUP_HEAVY_BODY_LEN) {
    return false;
  }
  const lastAt = Number(groupHeavyThrottleAtBySession.get(sessionKey) || 0);
  if (now - lastAt < GROUP_HEAVY_THROTTLE_MS) {
    groupHeavyThrottleAtBySession.set(sessionKey, now);
    return true;
  }
  groupHeavyThrottleAtBySession.set(sessionKey, now);
  return false;
}

function pickPromptVariant(sessionKey: string): "A" | "B" {
  let hash = 0;
  for (let i = 0; i < sessionKey.length; i += 1) {
    hash = ((hash << 5) - hash) + sessionKey.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) % 2 === 0 ? "A" : "B";
}

/**
 * Parse media keys from message content based on message type.
 */
function parseMediaKeys(
  content: string,
  messageType: string,
): {
  imageKey?: string;
  fileKey?: string;
  fileName?: string;
} {
  try {
    const parsed = JSON.parse(content);
    const imageKey = normalizeFeishuExternalKey(parsed.image_key);
    const fileKey = normalizeFeishuExternalKey(parsed.file_key);
    switch (messageType) {
      case "image":
        return { imageKey };
      case "file":
        return { fileKey, fileName: parsed.file_name };
      case "audio":
        return { fileKey };
      case "video":
        // Video has both file_key (video) and image_key (thumbnail)
        return { fileKey, imageKey };
      case "sticker":
        return { fileKey };
      default:
        return {};
    }
  } catch {
    return {};
  }
}

/**
 * Parse post (rich text) content and extract embedded image keys.
 * Post structure: { title?: string, content: [[{ tag, text?, image_key?, ... }]] }
 */
function parsePostContent(content: string): {
  textContent: string;
  imageKeys: string[];
  mentionedOpenIds: string[];
} {
  try {
    const parsed = JSON.parse(content);
    const title = parsed.title || "";
    const contentBlocks = parsed.content || [];
    let textContent = title ? `${title}\n\n` : "";
    const imageKeys: string[] = [];
    const mentionedOpenIds: string[] = [];

    for (const paragraph of contentBlocks) {
      if (Array.isArray(paragraph)) {
        for (const element of paragraph) {
          if (element.tag === "text") {
            textContent += element.text || "";
          } else if (element.tag === "a") {
            // Link: show text or href
            textContent += element.text || element.href || "";
          } else if (element.tag === "at") {
            // Mention: @username
            textContent += `@${element.user_name || element.user_id || ""}`;
            if (element.user_id) {
              mentionedOpenIds.push(element.user_id);
            }
          } else if (element.tag === "img" && element.image_key) {
            // Embedded image
            const imageKey = normalizeFeishuExternalKey(element.image_key);
            if (imageKey) {
              imageKeys.push(imageKey);
            }
          }
        }
        textContent += "\n";
      }
    }

    return {
      textContent: textContent.trim() || "[Rich text message]",
      imageKeys,
      mentionedOpenIds,
    };
  } catch {
    return { textContent: "[Rich text message]", imageKeys: [], mentionedOpenIds: [] };
  }
}

/**
 * Infer placeholder text based on message type.
 */
function inferPlaceholder(messageType: string): string {
  switch (messageType) {
    case "image":
      return "<media:image>";
    case "file":
      return "<media:document>";
    case "audio":
      return "<media:audio>";
    case "video":
      return "<media:video>";
    case "sticker":
      return "<media:sticker>";
    default:
      return "<media:document>";
  }
}

/**
 * Resolve media from a Feishu message, downloading and saving to disk.
 * Similar to Discord's resolveMediaList().
 */
async function resolveFeishuMediaList(params: {
  cfg: ClawdbotConfig;
  messageId: string;
  messageType: string;
  content: string;
  maxBytes: number;
  log?: (msg: string) => void;
  accountId?: string;
}): Promise<FeishuMediaInfo[]> {
  const { cfg, messageId, messageType, content, maxBytes, log, accountId } = params;

  // Only process media message types (including post for embedded images)
  const mediaTypes = ["image", "file", "audio", "video", "sticker", "post"];
  if (!mediaTypes.includes(messageType)) {
    return [];
  }

  const out: FeishuMediaInfo[] = [];
  const core = getFeishuRuntime();

  // Handle post (rich text) messages with embedded images
  if (messageType === "post") {
    const { imageKeys } = parsePostContent(content);
    if (imageKeys.length === 0) {
      return [];
    }

    log?.(`feishu: post message contains ${imageKeys.length} embedded image(s)`);

    for (const imageKey of imageKeys) {
      try {
        // Embedded images in post use messageResource API with image_key as file_key
        const result = await downloadMessageResourceFeishu({
          cfg,
          messageId,
          fileKey: imageKey,
          type: "image",
          accountId,
        });

        let contentType = result.contentType;
        if (!contentType) {
          contentType = await core.media.detectMime({ buffer: result.buffer });
        }

        const saved = await core.channel.media.saveMediaBuffer(
          result.buffer,
          contentType,
          "inbound",
          maxBytes,
        );

        out.push({
          path: saved.path,
          contentType: saved.contentType,
          placeholder: "<media:image>",
        });

        log?.(`feishu: downloaded embedded image ${imageKey}, saved to ${saved.path}`);
      } catch (err) {
        log?.(`feishu: failed to download embedded image ${imageKey}: ${String(err)}`);
      }
    }

    return out;
  }

  // Handle other media types
  const mediaKeys = parseMediaKeys(content, messageType);
  if (!mediaKeys.imageKey && !mediaKeys.fileKey) {
    return [];
  }

  try {
    let buffer: Buffer;
    let contentType: string | undefined;
    let fileName: string | undefined;

    // For message media, always use messageResource API
    // The image.get API is only for images uploaded via im/v1/images, not for message attachments
    const fileKey = mediaKeys.fileKey || mediaKeys.imageKey;
    if (!fileKey) {
      return [];
    }

    const resourceType = messageType === "image" ? "image" : "file";
    const result = await downloadMessageResourceFeishu({
      cfg,
      messageId,
      fileKey,
      type: resourceType,
      accountId,
    });
    buffer = result.buffer;
    contentType = result.contentType;
    fileName = result.fileName || mediaKeys.fileName;

    // Detect mime type if not provided
    if (!contentType) {
      contentType = await core.media.detectMime({ buffer });
    }

    // Save to disk using core's saveMediaBuffer
    const saved = await core.channel.media.saveMediaBuffer(
      buffer,
      contentType,
      "inbound",
      maxBytes,
      fileName,
    );

    out.push({
      path: saved.path,
      contentType: saved.contentType,
      placeholder: inferPlaceholder(messageType),
    });

    log?.(`feishu: downloaded ${messageType} media, saved to ${saved.path}`);
  } catch (err) {
    log?.(`feishu: failed to download ${messageType} media: ${String(err)}`);
  }

  return out;
}

/**
 * Build media payload for inbound context.
 * Similar to Discord's buildDiscordMediaPayload().
 */
export function parseFeishuMessageEvent(
  event: FeishuMessageEvent,
  botOpenId?: string,
): FeishuMessageContext {
  const rawContent = parseMessageContent(event.message.content, event.message.message_type);
  const mentionedBot = checkBotMentioned(event, botOpenId);
  const content = stripBotMention(rawContent, event.message.mentions);

  const ctx: FeishuMessageContext = {
    chatId: event.message.chat_id,
    messageId: event.message.message_id,
    senderId: event.sender.sender_id.user_id || event.sender.sender_id.open_id || "",
    senderOpenId: event.sender.sender_id.open_id || "",
    chatType: event.message.chat_type,
    mentionedBot,
    rootId: event.message.root_id || undefined,
    parentId: event.message.parent_id || undefined,
    content,
    contentType: event.message.message_type,
  };

  // Detect mention forward request: message mentions bot + at least one other user
  if (isMentionForwardRequest(event, botOpenId)) {
    const mentionTargets = extractMentionTargets(event, botOpenId);
    if (mentionTargets.length > 0) {
      ctx.mentionTargets = mentionTargets;
      // Extract message body (remove all @ placeholders)
      const allMentionKeys = (event.message.mentions ?? []).map((m) => m.key);
      (ctx as FeishuMessageContext & { mentionMessageBody?: string }).mentionMessageBody =
        extractMessageBody(content, allMentionKeys);
    }
  }

  return ctx;
}

export type FeishuCardActionEvent = {
  open_id?: string;
  user_id?: string;
  open_message_id?: string;
  open_chat_id?: string;
  tenant_key?: string;
  action?: {
    value?: {
      command?: string;
      task_id?: string;
      action?: string;
    };
  };
};

export async function handleFeishuCardAction(params: {
  cfg: ClawdbotConfig;
  event: FeishuCardActionEvent;
  runtime?: RuntimeEnv;
  accountId?: string;
}): Promise<void> {
  const { cfg, event, runtime, accountId } = params;
  const log = runtime?.log ?? console.log;
  const command = String(event.action?.value?.command || "").trim();
  if (!command || !isCommerceShopperCommand(command)) {
    log(`feishu[${accountId ?? "default"}]: ignored card action, unsupported command: ${command}`);
    return;
  }

  const operator = String(event.open_id || event.user_id || "group_user");
  const targetChat = String(event.open_chat_id || "");
  const replyToMessageId = String(event.open_message_id || "");
  const to = targetChat ? `chat:${targetChat}` : operator ? `user:${operator}` : "";
  if (!to) {
    log(`feishu[${accountId ?? "default"}]: ignored card action, missing target`);
    return;
  }

  try {
    const reply = await executeCommerceShopperCommand({
      content: command,
      operator,
      mediaPaths: [],
    });
    await sendMessageFeishu({
      cfg,
      to,
      text: reply.text,
      replyToMessageId: replyToMessageId || undefined,
      accountId,
    });
    for (const imagePath of reply.imagePaths ?? []) {
      try {
        const mediaBuffer = await fs.readFile(imagePath);
        await sendMediaFeishu({
          cfg,
          to,
          mediaBuffer,
          fileName: imagePath.split("/").pop() || "selected.png",
          replyToMessageId: replyToMessageId || undefined,
          accountId,
        });
      } catch (err) {
        await sendMessageFeishu({
          cfg,
          to,
          text: `⚠️ selected evidence image send failed: ${imagePath}`,
          replyToMessageId: replyToMessageId || undefined,
          accountId,
        });
        log(`feishu[${accountId ?? "default"}]: failed to send selected evidence image ${imagePath}: ${String(err)}`);
      }
    }
  } catch (err) {
    await sendMessageFeishu({
      cfg,
      to,
      text: `❌ commerce-travel-shopper card action failed: ${String(err)}`,
      replyToMessageId: replyToMessageId || undefined,
      accountId,
    });
  }
}

export async function handleFeishuMessage(params: {
  cfg: ClawdbotConfig;
  event: FeishuMessageEvent;
  botOpenId?: string;
  runtime?: RuntimeEnv;
  chatHistories?: Map<string, HistoryEntry[]>;
  accountId?: string;
}): Promise<void> {
  const { cfg, event, botOpenId, runtime, chatHistories, accountId } = params;

  // Resolve account with merged config
  const account = resolveFeishuAccount({ cfg, accountId });
  const feishuCfg = account.config;

  const log = runtime?.log ?? console.log;
  const error = runtime?.error ?? console.error;

  // Dedup check: skip if this message was already processed (memory + disk).
  const messageId = event.message.message_id;
  if (!(await tryRecordMessagePersistent(messageId, account.accountId, log))) {
    log(`feishu: skipping duplicate message ${messageId}`);
    return;
  }

  let ctx = parseFeishuMessageEvent(event, botOpenId);
  const isGroup = ctx.chatType === "group";
  const senderUserId = event.sender.sender_id.user_id?.trim() || undefined;

  // Resolve sender name in a non-blocking way: use cache immediately, refresh in background.
  const cachedSenderName = getCachedSenderName(ctx.senderOpenId);
  if (cachedSenderName) {
    ctx = { ...ctx, senderName: cachedSenderName };
  }
  maybeRefreshFeishuSenderNameInBackground({
    account,
    senderOpenId: ctx.senderOpenId,
    log,
    onPermissionError: (permissionError) => {
      const appKey = account.appId ?? "default";
      const now = Date.now();
      const lastNotified = permissionErrorNotifiedAt.get(appKey) ?? 0;
      if (now - lastNotified <= PERMISSION_ERROR_COOLDOWN_MS) {
        return;
      }
      permissionErrorNotifiedAt.set(appKey, now);
      const grantUrl = permissionError.grantUrl?.trim();
      const hintLine = grantUrl
        ? `管理员可在此授权：${grantUrl}`
        : "请管理员在飞书开放平台为应用补齐联系人读取权限。";
      void sendMessageFeishu({
        cfg,
        to: isGroup ? `chat:${ctx.chatId}` : `user:${ctx.senderOpenId}`,
        text: `⚠️ 当前消息处理中检测到飞书权限不足，可能影响回复速度或内容完整性。${hintLine}`,
        replyToMessageId: ctx.messageId,
        accountId: account.accountId,
      }).catch((err) => {
        log(`feishu[${account.accountId}]: permission warning notice failed: ${String(err)}`);
      });
    },
  });

  log(
    `feishu[${account.accountId}]: received message from ${ctx.senderOpenId} in ${ctx.chatId} (${ctx.chatType})`,
  );

  const quotedContentPromise: Promise<string | undefined> = ctx.parentId
    ? getMessageFeishu({
        cfg,
        messageId: ctx.parentId,
        accountId: account.accountId,
      })
        .then((quotedMsg) => quotedMsg?.content)
        .catch((err) => {
          log(`feishu[${account.accountId}]: failed to fetch quoted message: ${String(err)}`);
          return undefined;
        })
    : Promise.resolve(undefined);

  // Log mention targets if detected
  if (ctx.mentionTargets && ctx.mentionTargets.length > 0) {
    const names = ctx.mentionTargets.map((t) => t.name).join(", ");
    log(`feishu[${account.accountId}]: detected @ forward request, targets: [${names}]`);
  }

  const historyLimit = Math.max(
    0,
    feishuCfg?.historyLimit ?? cfg.messages?.groupChat?.historyLimit ?? DEFAULT_GROUP_HISTORY_LIMIT,
  );
  const groupConfig = isGroup
    ? resolveFeishuGroupConfig({ cfg: feishuCfg, groupId: ctx.chatId })
    : undefined;
  const dmPolicy = feishuCfg?.dmPolicy ?? "pairing";
  const configAllowFrom = feishuCfg?.allowFrom ?? [];
  const useAccessGroups = cfg.commands?.useAccessGroups !== false;

  if (isGroup) {
    const defaultGroupPolicy = resolveDefaultGroupPolicy(cfg);
    const { groupPolicy, providerMissingFallbackApplied } = resolveOpenProviderRuntimeGroupPolicy({
      providerConfigPresent: cfg.channels?.feishu !== undefined,
      groupPolicy: feishuCfg?.groupPolicy,
      defaultGroupPolicy,
    });
    warnMissingProviderGroupPolicyFallbackOnce({
      providerMissingFallbackApplied,
      providerKey: "feishu",
      accountId: account.accountId,
      log,
    });
    const groupAllowFrom = feishuCfg?.groupAllowFrom ?? [];
    // DEBUG: log(`feishu[${account.accountId}]: groupPolicy=${groupPolicy}`);

    // Check if this GROUP is allowed (groupAllowFrom contains group IDs like oc_xxx, not user IDs)
    const groupAllowed = isFeishuGroupAllowed({
      groupPolicy,
      allowFrom: groupAllowFrom,
      senderId: ctx.chatId, // Check group ID, not sender ID
      senderName: undefined,
    });

    if (!groupAllowed) {
      log(`feishu[${account.accountId}]: sender ${ctx.senderOpenId} not in group allowlist`);
      return;
    }

    // Additional sender-level allowlist check if group has specific allowFrom config
    const senderAllowFrom = groupConfig?.allowFrom ?? [];
    if (senderAllowFrom.length > 0) {
      const senderAllowed = isFeishuGroupAllowed({
        groupPolicy: "allowlist",
        allowFrom: senderAllowFrom,
        senderId: ctx.senderOpenId,
        senderIds: [senderUserId],
        senderName: ctx.senderName,
      });
      if (!senderAllowed) {
        log(`feishu: sender ${ctx.senderOpenId} not in group ${ctx.chatId} sender allowlist`);
        return;
      }
    }

    const { requireMention } = resolveFeishuReplyPolicy({
      isDirectMessage: false,
      globalConfig: feishuCfg,
      groupConfig,
    });

    if (requireMention && !ctx.mentionedBot) {
      log(
        `feishu[${account.accountId}]: message in group ${ctx.chatId} did not mention bot, recording to history`,
      );
      if (chatHistories) {
        recordPendingHistoryEntryIfEnabled({
          historyMap: chatHistories,
          historyKey: ctx.chatId,
          limit: historyLimit,
          entry: {
            sender: ctx.senderOpenId,
            body: `${ctx.senderName ?? ctx.senderOpenId}: ${ctx.content}`,
            timestamp: Date.now(),
            messageId: ctx.messageId,
          },
        });
      }
      return;
    }
  } else {
  }

  let delayedAckTimer: NodeJS.Timeout | undefined;
  const ephemeralMessageIds: string[] = [];
  try {
    const core = getFeishuRuntime();
    const shouldComputeCommandAuthorized = core.channel.commands.shouldComputeCommandAuthorized(
      ctx.content,
      cfg,
    );
    const storeAllowFrom =
      !isGroup &&
      dmPolicy !== "allowlist" &&
      (dmPolicy !== "open" || shouldComputeCommandAuthorized)
        ? await core.channel.pairing.readAllowFromStore("feishu").catch(() => [])
        : [];
    const effectiveDmAllowFrom = [...configAllowFrom, ...storeAllowFrom];
    const dmAllowed = resolveFeishuAllowlistMatch({
      allowFrom: effectiveDmAllowFrom,
      senderId: ctx.senderOpenId,
      senderIds: [senderUserId],
      senderName: ctx.senderName,
    }).allowed;

    if (!isGroup && dmPolicy !== "open" && !dmAllowed) {
      if (dmPolicy === "pairing") {
        const { code, created } = await core.channel.pairing.upsertPairingRequest({
          channel: "feishu",
          id: ctx.senderOpenId,
          meta: { name: ctx.senderName },
        });
        if (created) {
          log(`feishu[${account.accountId}]: pairing request sender=${ctx.senderOpenId}`);
          try {
            await sendMessageFeishu({
              cfg,
              to: `user:${ctx.senderOpenId}`,
              text: core.channel.pairing.buildPairingReply({
                channel: "feishu",
                idLine: `Your Feishu user id: ${ctx.senderOpenId}`,
                code,
              }),
              accountId: account.accountId,
            });
          } catch (err) {
            log(
              `feishu[${account.accountId}]: pairing reply failed for ${ctx.senderOpenId}: ${String(err)}`,
            );
          }
        }
      } else {
        log(
          `feishu[${account.accountId}]: blocked unauthorized sender ${ctx.senderOpenId} (dmPolicy=${dmPolicy})`,
        );
      }
      return;
    }

    const commandAllowFrom = isGroup
      ? (groupConfig?.allowFrom ?? configAllowFrom)
      : effectiveDmAllowFrom;
    const senderAllowedForCommands = resolveFeishuAllowlistMatch({
      allowFrom: commandAllowFrom,
      senderId: ctx.senderOpenId,
      senderIds: [senderUserId],
      senderName: ctx.senderName,
    }).allowed;
    const commandAuthorized = shouldComputeCommandAuthorized
      ? core.channel.commands.resolveCommandAuthorizedFromAuthorizers({
          useAccessGroups,
          authorizers: [
            { configured: commandAllowFrom.length > 0, allowed: senderAllowedForCommands },
          ],
        })
      : undefined;

    // Resolve media early so SHOP INGEST can use attachments directly.
    const mediaMaxBytes = (feishuCfg?.mediaMaxMb ?? 30) * 1024 * 1024; // 30MB default
    const mediaList = await resolveFeishuMediaList({
      cfg,
      messageId: ctx.messageId,
      messageType: event.message.message_type,
      content: event.message.content,
      maxBytes: mediaMaxBytes,
      log,
      accountId: account.accountId,
    });
    const mediaPayload = buildAgentMediaPayload(mediaList);

    if (isCommerceShopperCommand(ctx.content)) {
      const operator = ctx.senderOpenId || senderUserId || ctx.senderName || "group_user";
      try {
        const reply = await executeCommerceShopperCommand({
          content: ctx.content,
          operator,
          mediaPaths: mediaList.map((m) => m.path),
        });
        const to = isGroup ? `chat:${ctx.chatId}` : `user:${ctx.senderOpenId}`;
        await sendMessageFeishu({
          cfg,
          to,
          text: reply.text,
          replyToMessageId: ctx.messageId,
          accountId: account.accountId,
        });
        for (const imagePath of reply.imagePaths ?? []) {
          try {
            const mediaBuffer = await fs.readFile(imagePath);
            await sendMediaFeishu({
              cfg,
              to,
              mediaBuffer,
              fileName: imagePath.split("/").pop() || "selected.png",
              replyToMessageId: ctx.messageId,
              accountId: account.accountId,
            });
          } catch (err) {
            await sendMessageFeishu({
              cfg,
              to,
              text: `⚠️ selected evidence image send failed: ${imagePath}`,
              replyToMessageId: ctx.messageId,
              accountId: account.accountId,
            });
            log(`feishu[${account.accountId}]: failed to send selected evidence image ${imagePath}: ${String(err)}`);
          }
        }
      } catch (err) {
        await sendMessageFeishu({
          cfg,
          to: isGroup ? `chat:${ctx.chatId}` : `user:${ctx.senderOpenId}`,
          text: `❌ commerce-travel-shopper command failed: ${String(err)}`,
          replyToMessageId: ctx.messageId,
          accountId: account.accountId,
        });
      }
      return;
    }

    // In group chats, the session is scoped to the group, but the *speaker* is the sender.
    // Using a group-scoped From causes the agent to treat different users as the same person.
    const feishuFrom = `feishu:${ctx.senderOpenId}`;
    const feishuTo = isGroup ? `chat:${ctx.chatId}` : `user:${ctx.senderOpenId}`;

    // Resolve peer ID for session routing
    // When topicSessionMode is enabled, messages within a topic (identified by root_id)
    // get a separate session from the main group chat.
    let peerId = isGroup ? ctx.chatId : ctx.senderOpenId;
    let topicSessionMode: "enabled" | "disabled" = "disabled";
    if (isGroup && ctx.rootId) {
      const groupConfig = resolveFeishuGroupConfig({ cfg: feishuCfg, groupId: ctx.chatId });
      topicSessionMode = groupConfig?.topicSessionMode ?? feishuCfg?.topicSessionMode ?? "disabled";
      if (topicSessionMode === "enabled") {
        // Use chatId:topic:rootId as peer ID for topic-scoped sessions
        peerId = `${ctx.chatId}:topic:${ctx.rootId}`;
        log(`feishu[${account.accountId}]: topic session isolation enabled, peer=${peerId}`);
      }
    }

    let route = core.channel.routing.resolveAgentRoute({
      cfg,
      channel: "feishu",
      accountId: account.accountId,
      peer: {
        kind: isGroup ? "group" : "direct",
        id: peerId,
      },
      // Add parentPeer for binding inheritance in topic mode
      parentPeer:
        isGroup && ctx.rootId && topicSessionMode === "enabled"
          ? {
              kind: "group",
              id: ctx.chatId,
            }
          : null,
    });

    // Dynamic agent creation for DM users
    // When enabled, creates a unique agent instance with its own workspace for each DM user.
    let effectiveCfg = cfg;
    if (!isGroup && route.matchedBy === "default") {
      const dynamicCfg = feishuCfg?.dynamicAgentCreation as DynamicAgentCreationConfig | undefined;
      if (dynamicCfg?.enabled) {
        const runtime = getFeishuRuntime();
        const result = await maybeCreateDynamicAgent({
          cfg,
          runtime,
          senderOpenId: ctx.senderOpenId,
          dynamicCfg,
          log: (msg) => log(msg),
        });
        if (result.created) {
          effectiveCfg = result.updatedCfg;
          // Re-resolve route with updated config
          route = core.channel.routing.resolveAgentRoute({
            cfg: result.updatedCfg,
            channel: "feishu",
            accountId: account.accountId,
            peer: { kind: "direct", id: ctx.senderOpenId },
          });
          log(
            `feishu[${account.accountId}]: dynamic agent created, new route: ${route.sessionKey}`,
          );
        }
      }
    }

    const preview = ctx.content.replace(/\s+/g, " ").slice(0, 160);
    const inboundLabel = isGroup
      ? `Feishu[${account.accountId}] message in group ${ctx.chatId}`
      : `Feishu[${account.accountId}] DM from ${ctx.senderOpenId}`;

    core.system.enqueueSystemEvent(`${inboundLabel}: ${preview}`, {
      sessionKey: route.sessionKey,
      contextKey: `feishu:message:${ctx.chatId}:${ctx.messageId}`,
    });

    const quotedContent = await quotedContentPromise;

    const envelopeOptions = core.channel.reply.resolveEnvelopeFormatOptions(cfg);

    // Build message body with quoted content if available
    let messageBody = ctx.content;
    if (quotedContent) {
      messageBody = `[Replying to: "${quotedContent}"]\n\n${ctx.content}`;
    }

    // Include a readable speaker label so the model can attribute instructions.
    // (DMs already have per-sender sessions, but the prefix is still useful for clarity.)
    const speaker = ctx.senderName ?? ctx.senderOpenId;
    messageBody = `${speaker}: ${messageBody}`;

    // If there are mention targets, inform the agent that replies will auto-mention them
    if (ctx.mentionTargets && ctx.mentionTargets.length > 0) {
      const targetNames = ctx.mentionTargets.map((t) => t.name).join(", ");
      messageBody += `\n\n[System: Your reply will automatically @mention: ${targetNames}. Do not write @xxx yourself.]`;
    }

    const envelopeFrom = isGroup ? `${ctx.chatId}:${ctx.senderOpenId}` : ctx.senderOpenId;

    const body = core.channel.reply.formatAgentEnvelope({
      channel: "Feishu",
      from: envelopeFrom,
      timestamp: new Date(),
      envelope: envelopeOptions,
      body: messageBody,
    });

    let combinedBody = body;
    const historyKey = isGroup ? ctx.chatId : undefined;

    if (isGroup && historyKey && chatHistories) {
      combinedBody = buildPendingHistoryContextFromMap({
        historyMap: chatHistories,
        historyKey,
        limit: historyLimit,
        currentMessage: combinedBody,
        formatEntry: (entry: HistoryEntry) =>
          core.channel.reply.formatAgentEnvelope({
            channel: "Feishu",
            // Preserve speaker identity in group history as well.
            from: `${ctx.chatId}:${entry.sender}`,
            timestamp: entry.timestamp,
            body: entry.body,
            envelope: envelopeOptions,
          }),
      });
    }

    let burstCount = 1;
    if (!isGroup) {
      const merged = mergeDmBurstBody(route.sessionKey, combinedBody, Date.now());
      combinedBody = merged.mergedBody;
      burstCount = merged.burstCount;
    }

    const inboundHistory =
      isGroup && historyKey && historyLimit > 0 && chatHistories
        ? (chatHistories.get(historyKey) ?? []).map((entry: HistoryEntry) => ({
            sender: entry.sender,
            body: entry.body,
            timestamp: entry.timestamp,
          }))
        : undefined;

    const ctxPayload = core.channel.reply.finalizeInboundContext({
      Body: combinedBody,
      BodyForAgent: ctx.content,
      InboundHistory: inboundHistory,
      RawBody: ctx.content,
      CommandBody: ctx.content,
      From: feishuFrom,
      To: feishuTo,
      SessionKey: route.sessionKey,
      AccountId: route.accountId,
      ChatType: isGroup ? "group" : "direct",
      GroupSubject: isGroup ? ctx.chatId : undefined,
      SenderName: ctx.senderName ?? ctx.senderOpenId,
      SenderId: ctx.senderOpenId,
      Provider: "feishu" as const,
      Surface: "feishu" as const,
      MessageSid: ctx.messageId,
      ReplyToBody: quotedContent ?? undefined,
      Timestamp: Date.now(),
      WasMentioned: ctx.mentionedBot,
      CommandAuthorized: commandAuthorized,
      OriginatingChannel: "feishu" as const,
      OriginatingTo: feishuTo,
      ...mediaPayload,
    });

    const dispatchStartedAt = Date.now();
    const laneEnabled = feishuCfg?.sessionSerialDispatch !== false;
    const laneConcurrency = Math.max(
      1,
      Math.min(
        8,
        Math.floor(
          Number(
            (feishuCfg as { sessionDispatchConcurrency?: number } | undefined)
              ?.sessionDispatchConcurrency ?? 1,
          ),
        ),
      ),
    );
    const hadPendingLane = hasPendingLaneWork(route.sessionKey);
    const dispatchPriority = !isGroup && burstCount > 1 ? 1 : 0;
    if (isGroup && shouldThrottleGroupHeavyMessage({
      sessionKey: route.sessionKey,
      body: combinedBody,
      now: dispatchStartedAt,
      hadPendingLane,
    })) {
      await sendMessageFeishu({
        cfg,
        to: feishuTo,
        text: "⏳ 群内短时间高频重任务请求已节流，本次保留最新请求，稍后统一回传结果。",
        replyToMessageId: ctx.messageId,
        accountId: account.accountId,
      });
      return;
    }
    log(
      `feishu[${account.accountId}]: dispatch start (session=${route.sessionKey}, messageId=${ctx.messageId}, laneEnabled=${laneEnabled}, hadPendingLane=${hadPendingLane}, priority=${dispatchPriority})`,
    );

    const isLightweight = ctx.content.trim().length <= LIGHTWEIGHT_QUERY_MAX_LEN &&
      LIGHTWEIGHT_QUERY_PATTERNS.some((p) => p.test(ctx.content.trim()));
    if (!isGroup && !hadPendingLane && !isLightweight) {
      delayedAckTimer = setTimeout(() => {
        // Skip standalone ACK if streaming card is already active (card itself serves as ACK)
        if ((globalThis as any).__ocFeishuStreamingActive?.has(ctx.chatId)) {
          return;
        }
        void sendMessageFeishu({
          cfg,
          to: feishuTo,
          text: "⚡ 已收到，正在处理中，我会尽快先给你关键结论。",
          replyToMessageId: ctx.messageId,
          accountId: account.accountId,
        }).then((result) => {
          if (result?.messageId && result.messageId !== "unknown") {
            ephemeralMessageIds.push(result.messageId);
          }
        }).catch((err) => {
          log(`feishu[${account.accountId}]: delayed dm ack failed: ${String(err)}`);
        });
      }, DM_ACK_DELAY_MS);
    }

    const executeDispatch = async () => {
      const { dispatcher, replyOptions, markDispatchIdle } = createFeishuReplyDispatcher({
        cfg,
        agentId: route.agentId,
        runtime: runtime as RuntimeEnv,
        chatId: ctx.chatId,
        replyToMessageId: ctx.messageId,
        mentionTargets: ctx.mentionTargets,
        accountId: account.accountId,
      });

      log(`feishu[${account.accountId}]: dispatching to agent (session=${route.sessionKey})`);

      const result = await core.channel.reply.dispatchReplyFromConfig({
        ctx: ctxPayload,
        cfg,
        dispatcher,
        replyOptions,
      });

      markDispatchIdle();

      if (isGroup && historyKey && chatHistories) {
        clearHistoryEntriesIfEnabled({
          historyMap: chatHistories,
          historyKey,
          limit: historyLimit,
        });
      }

      return result;
    };

    const laneWaitStartedAt = Date.now();
    if (laneEnabled && hadPendingLane && shouldSendQueueNotice(route.sessionKey, Date.now())) {
      const etaSec = formatEtaSeconds(
        estimateSessionWaitMs(route.sessionKey, Math.max(1, getLaneQueueDepth(route.sessionKey)), isGroup),
      );
      const variant = pickPromptVariant(route.sessionKey);
      const queueText = isGroup
        ? `⏳ 当前会话有任务处理中，本条消息已入队，预计约 ${etaSec} 秒后开始处理。`
        : (burstCount > 1
            ? (variant === "A"
                ? `⏳ 已识别到你在连续补充（第${burstCount}条），当前已入队，预计约 ${etaSec} 秒后处理。`
                : `⏳ 你这几条消息我会合并处理（第${burstCount}条补充），预计约 ${etaSec} 秒后开始回传。`)
            : (variant === "A"
                ? `⏳ 上一条消息仍在处理，本条已入队，预计约 ${etaSec} 秒后处理。`
                : `⏳ 正在处理上一条，本条已排队，预计约 ${etaSec} 秒后给你反馈。`));
      void sendMessageFeishu({
        cfg,
        to: feishuTo,
        text: queueText,
        replyToMessageId: ctx.messageId,
        accountId: account.accountId,
      }).then((result) => {
        if (result?.messageId && result.messageId !== "unknown") {
          ephemeralMessageIds.push(result.messageId);
        }
      }).catch((err) => {
        log(`feishu[${account.accountId}]: queue notice failed: ${String(err)}`);
      });
    }
    const { queuedFinal, counts } = laneEnabled
      ? await runInSessionDispatchLane(route.sessionKey, async () => {
          const laneAcquireMs = hadPendingLane ? Date.now() - laneWaitStartedAt : 0;
          if (hadPendingLane) {
            log(
              `feishu[${account.accountId}]: lane acquired (session=${route.sessionKey}, waitedMs=${laneAcquireMs})`,
            );
          }
          if (hadPendingLane) {
            log(
              `feishu[${account.accountId}]: waiting for prior in-flight run (session=${route.sessionKey})`,
            );
          }
          return executeDispatch();
        }, laneConcurrency)
      : await executeDispatch();
    if (delayedAckTimer) {
      clearTimeout(delayedAckTimer);
    }
    const laneWaitMs = hadPendingLane ? Date.now() - laneWaitStartedAt : 0;
    const dispatchLatencyMs = Date.now() - dispatchStartedAt;
    updateSessionLatencyEstimate(route.sessionKey, dispatchLatencyMs, isGroup);
    if (dispatchLatencyMs >= SLOW_DISPATCH_WARN_MS || laneWaitMs >= SLOW_LANE_WAIT_WARN_MS) {
      log(
        `feishu[${account.accountId}]: slow dispatch warning (session=${route.sessionKey}, messageId=${ctx.messageId}, laneWaitMs=${laneWaitMs}, dispatchLatencyMs=${dispatchLatencyMs}, thresholds={laneWait:${SLOW_LANE_WAIT_WARN_MS},dispatch:${SLOW_DISPATCH_WARN_MS}})`,
      );
    }

    if (queuedFinal || Number(counts.final || 0) > 0) {
      clearPendingFinalNotice(route.sessionKey);
      log(
        `feishu[${account.accountId}]: final reply observed; cleared watchdog timer (session=${route.sessionKey})`,
      );
    } else {
      const watchdogSec = readResponseWatchdogSeconds(feishuCfg);
      log(
        `feishu[${account.accountId}]: no immediate final reply; scheduling watchdog (session=${route.sessionKey}, watchdogSec=${watchdogSec})`,
      );
      const firstDelayMs = !isGroup ? Math.min(watchdogSec * 1000, 15_000) : watchdogSec * 1000;
      schedulePendingFinalNotice({
        sessionKey: route.sessionKey,
        delayMs: firstDelayMs,
        log,
        sendNotice: async () => {
          const pendingCount = Number(pendingFinalNoticeCounts.get(route.sessionKey) || 1);
          const etaSec = formatEtaSeconds(estimateSessionWaitMs(route.sessionKey, Math.max(1, pendingCount), isGroup));
          const result = await sendMessageFeishu({
            cfg,
            to: feishuTo,
            text: !isGroup
              ? `⏳ 仍在处理中（第${pendingCount}次提醒），预计约 ${etaSec} 秒内继续返回结果。`
              : `⏳ 任务处理中（第${pendingCount}次提醒），预计约 ${etaSec} 秒内继续回传。`,
            replyToMessageId: ctx.messageId,
            accountId: account.accountId,
          });
          if (result?.messageId && result.messageId !== "unknown") {
            ephemeralMessageIds.push(result.messageId);
          }
          const nextDelay = resolveNextPendingNoticeDelayMs(pendingCount, firstDelayMs);
          if (nextDelay > 0 && !pendingFinalNoticeTimers.has(route.sessionKey)) {
            schedulePendingFinalNotice({
              sessionKey: route.sessionKey,
              delayMs: nextDelay,
              log,
              sendNotice: async () => {
                const nextCount = Number(pendingFinalNoticeCounts.get(route.sessionKey) || 1);
                const nextEtaSec = formatEtaSeconds(
                  estimateSessionWaitMs(route.sessionKey, Math.max(1, nextCount), isGroup),
                );
                const nextResult = await sendMessageFeishu({
                  cfg,
                  to: feishuTo,
                  text: !isGroup
                    ? `⏳ 仍在处理中（第${nextCount}次提醒），预计约 ${nextEtaSec} 秒内继续返回结果。`
                    : `⏳ 任务处理中（第${nextCount}次提醒），预计约 ${nextEtaSec} 秒内继续回传。`,
                  replyToMessageId: ctx.messageId,
                  accountId: account.accountId,
                });
                if (nextResult?.messageId && nextResult.messageId !== "unknown") {
                  ephemeralMessageIds.push(nextResult.messageId);
                }
              },
            });
          }
        },
      });
    }

    log(
      `feishu[${account.accountId}]: dispatch complete (queuedFinal=${queuedFinal}, replies=${counts.final}, laneWaitMs=${laneWaitMs}, dispatchLatencyMs=${dispatchLatencyMs})`,
    );

    // UX: Clean up ephemeral status messages (ACK, queue notices, watchdog reminders)
    // after final reply is delivered, so the user only sees the actual response.
    if (ephemeralMessageIds.length > 0) {
      const idsToDelete = [...ephemeralMessageIds];
      ephemeralMessageIds.length = 0;
      // Small delay to ensure the final reply card has been visually rendered first
      setTimeout(() => {
        log(
          `feishu[${account.accountId}]: cleaning up ${idsToDelete.length} ephemeral message(s) (session=${route.sessionKey})`,
        );
        for (const msgId of idsToDelete) {
          void deleteMessageFeishu({ cfg, messageId: msgId, accountId: account.accountId }).catch(
            (err) => log(`feishu[${account.accountId}]: ephemeral cleanup failed for ${msgId}: ${String(err)}`),
          );
        }
      }, 1500);
    }
  } catch (err) {
    if (typeof delayedAckTimer !== "undefined") {
      clearTimeout(delayedAckTimer);
    }
    error(`feishu[${account.accountId}]: failed to dispatch message: ${String(err)}`);
  }
}
