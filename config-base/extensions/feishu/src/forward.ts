import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuForwardSchema, type FeishuForwardParams } from "./forward-schema.js";
import { normalizeFeishuTarget } from "./targets.js";
import { resolveReceiveIdType } from "./targets.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function forwardMessage(client: Lark.Client, messageId: string, target: string) {
  const receiveId = normalizeFeishuTarget(target);
  if (!receiveId) throw new Error(`Invalid target: ${target}`);
  const receiveIdType = resolveReceiveIdType(receiveId);

  const res = await (client as any).im.message.forward({
    path: { message_id: messageId },
    data: { receive_id: receiveId },
    params: { receive_id_type: receiveIdType },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    message_id: res.data?.message_id,
    success: true,
  };
}

async function mergeForward(client: Lark.Client, messageIds: string[], target: string) {
  const receiveId = normalizeFeishuTarget(target);
  if (!receiveId) throw new Error(`Invalid target: ${target}`);
  const receiveIdType = resolveReceiveIdType(receiveId);

  const res = await (client as any).im.message.mergeForward({
    data: {
      receive_id: receiveId,
      message_id_list: messageIds,
    },
    params: { receive_id_type: receiveIdType },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    message_id: res.data?.message_id,
    success: true,
  };
}

// ============ Tool Registration ============

export function registerFeishuForwardTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_forward",
      label: "Feishu Forward",
      description:
        "Forward or merge-forward Feishu messages to another chat or user. Actions: forward, merge_forward",
      parameters: FeishuForwardSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuForwardParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "forward":
              return json(await forwardMessage(client, p.message_id, p.target));
            case "merge_forward":
              return json(await mergeForward(client, p.message_ids, p.target));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_forward" },
  );

  api.logger.info?.("feishu_forward: Registered feishu_forward tool");
}
