import type { ChannelMeta, ChannelPlugin, ClawdbotConfig } from "openclaw/plugin-sdk";
import {
  buildBaseChannelStatusSummary,
  createDefaultChannelRuntimeState,
  DEFAULT_ACCOUNT_ID,
  PAIRING_APPROVED_MESSAGE,
  resolveAllowlistProviderRuntimeGroupPolicy,
  resolveDefaultGroupPolicy,
} from "openclaw/plugin-sdk";
import {
  resolveFeishuAccount,
  resolveFeishuCredentials,
  listFeishuAccountIds,
  resolveDefaultFeishuAccountId,
} from "./accounts.js";
import {
  listFeishuDirectoryPeers,
  listFeishuDirectoryGroups,
  listFeishuDirectoryPeersLive,
  listFeishuDirectoryGroupsLive,
} from "./directory.js";
import { feishuOnboardingAdapter } from "./onboarding.js";
import { feishuOutbound } from "./outbound.js";
import { resolveFeishuGroupToolPolicy } from "./policy.js";
import { probeFeishu } from "./probe.js";
import { sendMessageFeishu } from "./send.js";
import { normalizeFeishuTarget, looksLikeFeishuId, formatFeishuTarget } from "./targets.js";
import type { ResolvedFeishuAccount, FeishuConfig } from "./types.js";

const meta: ChannelMeta = {
  id: "feishu",
  label: "Feishu",
  selectionLabel: "Feishu/Lark (飞书)",
  docsPath: "/channels/feishu",
  docsLabel: "feishu",
  blurb: "飞书/Lark enterprise messaging.",
  aliases: ["lark"],
  order: 70,
};

function likelyPlainSecret(value: unknown): boolean {
  const text = String(value ?? "").trim();
  if (!text) return false;
  if (text.startsWith("${") && text.endsWith("}")) return false;
  if (text.startsWith("env:")) return false;
  if (text.startsWith("secret:")) return false;
  if (text.includes("{{") || text.includes("}}")) return false;
  return true;
}

export const feishuPlugin: ChannelPlugin<ResolvedFeishuAccount> = {
  id: "feishu",
  meta: {
    ...meta,
  },
  pairing: {
    idLabel: "feishuUserId",
    normalizeAllowEntry: (entry) => entry.replace(/^(feishu|user|open_id):/i, ""),
    notifyApproval: async ({ cfg, id }) => {
      await sendMessageFeishu({
        cfg,
        to: id,
        text: PAIRING_APPROVED_MESSAGE,
      });
    },
  },
  capabilities: {
    chatTypes: ["direct", "channel"],
    polls: false,
    threads: true,
    media: true,
    reactions: true,
    edit: true,
    reply: true,
  },
  agentPrompt: {
    messageToolHints: () => [
      "- Feishu targeting: omit `target` to reply to the current conversation (auto-inferred). Explicit targets: `user:open_id` or `chat:chat_id`.",
      "- Feishu supports interactive cards for rich messages.",
      "- If user asks to '创建飞书文档/云文档/docx', you MUST call `feishu_doc` action `create` with `title` + `content`. Do NOT create local `.md` files as a replacement.",
      "- To send images/screenshots/charts to a Feishu conversation, use the `feishu_image` tool with action `send_image` and provide the image URL. Do NOT use markdown image syntax `![](url)` — it will only show as text.",
      "- To send files (PDF, doc, etc.) to a conversation, use `feishu_image` tool with action `send_file`.",
      "- To create a Feishu cloud document WITH content, use `feishu_doc` with action `create` and include both `title` and `content` (markdown).",
      "- Calendar: use `feishu_calendar` for list_calendars, list_events, create_event, delete_event, search_calendars.",
      "- Approvals: use `feishu_approval` for list_definitions, get_definition, list_instances, get_instance, create_instance, approve, reject.",
      "- Search: use `feishu_search` for search_messages, search_docs, search_chats.",
      "- Groups: use `feishu_group` for list_chats, get_chat, create_chat, update_chat, add_members, remove_members, list_members, disband_chat.",
      "- Tasks: use `feishu_task` for create, get, list, complete, uncomplete, delete, add_members.",
      "- Forward: use `feishu_forward` for forward (single message) or merge_forward (multiple messages).",
      "- Webhook: use `feishu_webhook` to send messages to external incoming webhook URLs.",
      "- Video conference: use `feishu_vc` for create_meeting, get_meeting, list_meetings, end_meeting.",
      "- Attendance: use `feishu_attendance` for list_groups, get_user_stats, get_user_tasks.",
      "- App management: use `feishu_app` for list_apps, get_app, check_visibility, list_app_versions.",
    ],
  },
  groups: {
    resolveToolPolicy: resolveFeishuGroupToolPolicy,
  },
  reload: { configPrefixes: ["channels.feishu"] },
  configSchema: {
    schema: {
      type: "object",
      additionalProperties: false,
      properties: {
        enabled: { type: "boolean" },
        appId: { type: "string" },
        appSecret: { type: "string" },
        encryptKey: { type: "string" },
        verificationToken: { type: "string" },
        domain: {
          oneOf: [
            { type: "string", enum: ["feishu", "lark"] },
            { type: "string", format: "uri", pattern: "^https://" },
          ],
        },
        connectionMode: { type: "string", enum: ["websocket", "webhook"] },
        webhookPath: { type: "string" },
        webhookHost: { type: "string" },
        webhookPort: { type: "integer", minimum: 1 },
        dmPolicy: { type: "string", enum: ["open", "pairing", "allowlist"] },
        allowFrom: { type: "array", items: { oneOf: [{ type: "string" }, { type: "number" }] } },
        groupPolicy: { type: "string", enum: ["open", "allowlist", "disabled"] },
        groupAllowFrom: {
          type: "array",
          items: { oneOf: [{ type: "string" }, { type: "number" }] },
        },
        requireMention: { type: "boolean" },
        topicSessionMode: { type: "string", enum: ["disabled", "enabled"] },
        historyLimit: { type: "integer", minimum: 0 },
        dmHistoryLimit: { type: "integer", minimum: 0 },
        textChunkLimit: { type: "integer", minimum: 1 },
        chunkMode: { type: "string", enum: ["length", "newline"] },
        mediaMaxMb: { type: "number", minimum: 0 },
        responseWatchdogSec: { type: "integer", minimum: 10, maximum: 300 },
        sessionSerialDispatch: { type: "boolean" },
        renderMode: { type: "string", enum: ["auto", "raw", "card"] },
        accounts: {
          type: "object",
          additionalProperties: {
            type: "object",
            properties: {
              enabled: { type: "boolean" },
              name: { type: "string" },
              appId: { type: "string" },
              appSecret: { type: "string" },
              encryptKey: { type: "string" },
              verificationToken: { type: "string" },
              domain: { type: "string", enum: ["feishu", "lark"] },
              connectionMode: { type: "string", enum: ["websocket", "webhook"] },
              webhookHost: { type: "string" },
              webhookPath: { type: "string" },
              webhookPort: { type: "integer", minimum: 1 },
              responseWatchdogSec: { type: "integer", minimum: 10, maximum: 300 },
              sessionSerialDispatch: { type: "boolean" },
            },
          },
        },
      },
    },
  },
  config: {
    listAccountIds: (cfg) => listFeishuAccountIds(cfg),
    resolveAccount: (cfg, accountId) => resolveFeishuAccount({ cfg, accountId }),
    defaultAccountId: (cfg) => resolveDefaultFeishuAccountId(cfg),
    setAccountEnabled: ({ cfg, accountId, enabled }) => {
      const account = resolveFeishuAccount({ cfg, accountId });
      const isDefault = accountId === DEFAULT_ACCOUNT_ID;

      if (isDefault) {
        // For default account, set top-level enabled
        return {
          ...cfg,
          channels: {
            ...cfg.channels,
            feishu: {
              ...cfg.channels?.feishu,
              enabled,
            },
          },
        };
      }

      // For named accounts, set enabled in accounts[accountId]
      const feishuCfg = cfg.channels?.feishu as FeishuConfig | undefined;
      return {
        ...cfg,
        channels: {
          ...cfg.channels,
          feishu: {
            ...feishuCfg,
            accounts: {
              ...feishuCfg?.accounts,
              [accountId]: {
                ...feishuCfg?.accounts?.[accountId],
                enabled,
              },
            },
          },
        },
      };
    },
    deleteAccount: ({ cfg, accountId }) => {
      const isDefault = accountId === DEFAULT_ACCOUNT_ID;

      if (isDefault) {
        // Delete entire feishu config
        const next = { ...cfg } as ClawdbotConfig;
        const nextChannels = { ...cfg.channels };
        delete (nextChannels as Record<string, unknown>).feishu;
        if (Object.keys(nextChannels).length > 0) {
          next.channels = nextChannels;
        } else {
          delete next.channels;
        }
        return next;
      }

      // Delete specific account from accounts
      const feishuCfg = cfg.channels?.feishu as FeishuConfig | undefined;
      const accounts = { ...feishuCfg?.accounts };
      delete accounts[accountId];

      return {
        ...cfg,
        channels: {
          ...cfg.channels,
          feishu: {
            ...feishuCfg,
            accounts: Object.keys(accounts).length > 0 ? accounts : undefined,
          },
        },
      };
    },
    isConfigured: (account) => account.configured,
    describeAccount: (account) => ({
      accountId: account.accountId,
      enabled: account.enabled,
      configured: account.configured,
      name: account.name,
      appId: account.appId,
      domain: account.domain,
    }),
    resolveAllowFrom: ({ cfg, accountId }) => {
      const account = resolveFeishuAccount({ cfg, accountId });
      return (account.config?.allowFrom ?? []).map((entry) => String(entry));
    },
    formatAllowFrom: ({ allowFrom }) =>
      allowFrom
        .map((entry) => String(entry).trim())
        .filter(Boolean)
        .map((entry) => entry.toLowerCase()),
  },
  security: {
    collectWarnings: ({ cfg, accountId }) => {
      const account = resolveFeishuAccount({ cfg, accountId });
      const feishuCfg = account.config;
      const warnings: string[] = [];
      const defaultGroupPolicy = resolveDefaultGroupPolicy(cfg);
      const { groupPolicy } = resolveAllowlistProviderRuntimeGroupPolicy({
        providerConfigPresent: cfg.channels?.feishu !== undefined,
        groupPolicy: feishuCfg?.groupPolicy,
        defaultGroupPolicy,
      });
      if (groupPolicy === "open") {
        warnings.push(
          `- Feishu[${account.accountId}] groups: groupPolicy="open" allows any member to trigger (mention-gated). Set channels.feishu.groupPolicy="allowlist" + channels.feishu.groupAllowFrom to restrict senders.`,
        );
      }

      if (likelyPlainSecret(account.appSecret)) {
        warnings.push(
          `- Feishu[${account.accountId}] appSecret appears to be plaintext. Prefer secret refs (e.g. env:FEISHU_APP_SECRET or \${FEISHU_APP_SECRET}).`,
        );
      }
      if (likelyPlainSecret(account.verificationToken)) {
        warnings.push(
          `- Feishu[${account.accountId}] verificationToken appears to be plaintext. Prefer secret refs for rotation hygiene.`,
        );
      }
      return warnings;
    },
  },
  setup: {
    resolveAccountId: () => DEFAULT_ACCOUNT_ID,
    applyAccountConfig: ({ cfg, accountId }) => {
      const isDefault = !accountId || accountId === DEFAULT_ACCOUNT_ID;

      if (isDefault) {
        return {
          ...cfg,
          channels: {
            ...cfg.channels,
            feishu: {
              ...cfg.channels?.feishu,
              enabled: true,
            },
          },
        };
      }

      const feishuCfg = cfg.channels?.feishu as FeishuConfig | undefined;
      return {
        ...cfg,
        channels: {
          ...cfg.channels,
          feishu: {
            ...feishuCfg,
            accounts: {
              ...feishuCfg?.accounts,
              [accountId]: {
                ...feishuCfg?.accounts?.[accountId],
                enabled: true,
              },
            },
          },
        },
      };
    },
  },
  onboarding: feishuOnboardingAdapter,
  messaging: {
    normalizeTarget: (raw) => normalizeFeishuTarget(raw) ?? undefined,
    targetResolver: {
      looksLikeId: looksLikeFeishuId,
      hint: "<chatId|user:openId|chat:chatId>",
    },
  },
  directory: {
    self: async () => null,
    listPeers: async ({ cfg, query, limit, accountId }) =>
      listFeishuDirectoryPeers({
        cfg,
        query: query ?? undefined,
        limit: limit ?? undefined,
        accountId: accountId ?? undefined,
      }),
    listGroups: async ({ cfg, query, limit, accountId }) =>
      listFeishuDirectoryGroups({
        cfg,
        query: query ?? undefined,
        limit: limit ?? undefined,
        accountId: accountId ?? undefined,
      }),
    listPeersLive: async ({ cfg, query, limit, accountId }) =>
      listFeishuDirectoryPeersLive({
        cfg,
        query: query ?? undefined,
        limit: limit ?? undefined,
        accountId: accountId ?? undefined,
      }),
    listGroupsLive: async ({ cfg, query, limit, accountId }) =>
      listFeishuDirectoryGroupsLive({
        cfg,
        query: query ?? undefined,
        limit: limit ?? undefined,
        accountId: accountId ?? undefined,
      }),
  },
  outbound: feishuOutbound,
  status: {
    defaultRuntime: createDefaultChannelRuntimeState(DEFAULT_ACCOUNT_ID, { port: null }),
    buildChannelSummary: ({ snapshot }) => ({
      ...buildBaseChannelStatusSummary(snapshot),
      port: snapshot.port ?? null,
      probe: snapshot.probe,
      lastProbeAt: snapshot.lastProbeAt ?? null,
    }),
    probeAccount: async ({ account }) => await probeFeishu(account),
    buildAccountSnapshot: ({ account, runtime, probe }) => ({
      accountId: account.accountId,
      enabled: account.enabled,
      configured: account.configured,
      name: account.name,
      appId: account.appId,
      domain: account.domain,
      running: runtime?.running ?? false,
      lastStartAt: runtime?.lastStartAt ?? null,
      lastStopAt: runtime?.lastStopAt ?? null,
      lastError: runtime?.lastError ?? null,
      port: runtime?.port ?? null,
      probe,
    }),
  },
  gateway: {
    startAccount: async (ctx) => {
      const { monitorFeishuProvider } = await import("./monitor.js");
      const account = resolveFeishuAccount({ cfg: ctx.cfg, accountId: ctx.accountId });
      const port = account.config?.webhookPort ?? null;
      ctx.setStatus({ accountId: ctx.accountId, port });
      ctx.log?.info(
        `starting feishu[${ctx.accountId}] (mode: ${account.config?.connectionMode ?? "websocket"})`,
      );
      return monitorFeishuProvider({
        config: ctx.cfg,
        runtime: ctx.runtime,
        abortSignal: ctx.abortSignal,
        accountId: ctx.accountId,
      });
    },
  },
};
