import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { FeishuWebhookSchema, type FeishuWebhookParams } from "./webhook-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function sendWebhook(webhookUrl: string, msgType: string, content: string) {
  let body: any;
  if (msgType === "text") {
    body = { msg_type: "text", content: { text: content } };
  } else if (msgType === "post" || msgType === "interactive") {
    try {
      const parsed = JSON.parse(content);
      body = { msg_type: msgType, ...(msgType === "interactive" ? { card: parsed } : { content: parsed }) };
    } catch {
      throw new Error(`Content must be valid JSON for msg_type "${msgType}"`);
    }
  } else {
    body = { msg_type: "text", content: { text: content } };
  }

  const res = await fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({ StatusCode: res.status })) as any;
  if (data.code !== undefined && data.code !== 0) {
    throw new Error(`Webhook failed: ${data.msg || `code ${data.code}`}`);
  }
  if (!res.ok) {
    throw new Error(`Webhook HTTP ${res.status}: ${JSON.stringify(data)}`);
  }

  return { success: true, status: res.status };
}

// ============ Tool Registration ============

export function registerFeishuWebhookTools(api: OpenClawPluginApi) {
  if (!api.config) return;

  api.registerTool(
    {
      name: "feishu_webhook",
      label: "Feishu Webhook",
      description:
        "Send messages to external systems via Feishu incoming webhook URL. Supports text, post (rich text), and interactive (card) message types.",
      parameters: FeishuWebhookSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuWebhookParams;
        try {
          return json(await sendWebhook(p.webhook_url, p.msg_type ?? "text", p.content));
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_webhook" },
  );

  api.logger.info?.("feishu_webhook: Registered feishu_webhook tool");
}
