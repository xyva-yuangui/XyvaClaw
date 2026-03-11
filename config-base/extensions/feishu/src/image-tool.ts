import { Type, type Static } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { sendMediaFeishu } from "./media.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

const FeishuImageSchema = Type.Union([
  Type.Object({
    action: Type.Literal("send_image"),
    image_url: Type.String({
      description:
        "URL of the image to send (http/https). The image will be downloaded, uploaded to Feishu, and sent as a native image message.",
    }),
    target: Type.String({
      description:
        "Target conversation. Use the OriginatingTo value from your context (e.g. 'user:ou_xxx' for DM or 'chat:oc_xxx' for group).",
    }),
  }),
  Type.Object({
    action: Type.Literal("send_file"),
    file_url: Type.String({
      description: "URL of the file to send (http/https). Will be uploaded and sent as a file message.",
    }),
    file_name: Type.Optional(
      Type.String({ description: "File name with extension (e.g. report.pdf). Auto-detected from URL if omitted." }),
    ),
    target: Type.String({
      description:
        "Target conversation. Use the OriginatingTo value from your context (e.g. 'user:ou_xxx' for DM or 'chat:oc_xxx' for group).",
    }),
  }),
]);

type FeishuImageParams = Static<typeof FeishuImageSchema>;

export function registerFeishuImageTool(api: OpenClawPluginApi) {
  if (!api.config) {
    api.logger.debug?.("feishu_image: No config available, skipping image tool");
    return;
  }

  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) {
    api.logger.debug?.("feishu_image: No Feishu accounts configured, skipping image tool");
    return;
  }

  const firstAccount = accounts[0];
  const mediaMaxBytes = (firstAccount.config?.mediaMaxMb ?? 30) * 1024 * 1024;

  api.registerTool(
    {
      name: "feishu_image",
      label: "Feishu Image/File Sender",
      description:
        "Send images or files as native Feishu messages (not markdown links). Use this when you need to send an image preview, screenshot, chart, or file attachment to the current Feishu conversation. Actions: send_image, send_file",
      parameters: FeishuImageSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuImageParams;
        const cfg = api.config!;
        const accountId = firstAccount.accountId;

        const target = (p as any).target as string;
        if (!target?.trim()) {
          return json({ error: "target is required. Use the OriginatingTo value from your context (e.g. 'user:ou_xxx' or 'chat:oc_xxx')." });
        }

        try {
          switch (p.action) {
            case "send_image": {
              const result = await sendMediaFeishu({
                cfg,
                to: target,
                mediaUrl: p.image_url,
                fileName: extractFileName(p.image_url, "image.png"),
                accountId,
              });
              return json({
                success: true,
                message_id: result.messageId,
                chat_id: result.chatId,
                note: "Image sent as native Feishu image message.",
              });
            }
            case "send_file": {
              const fileName = p.file_name || extractFileName(p.file_url, "file");
              const result = await sendMediaFeishu({
                cfg,
                to: target,
                mediaUrl: p.file_url,
                fileName,
                accountId,
              });
              return json({
                success: true,
                message_id: result.messageId,
                chat_id: result.chatId,
                note: `File "${fileName}" sent as native Feishu file message.`,
              });
            }
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_image" },
  );

  api.logger.info?.("feishu_image: Registered feishu_image tool");
}

function extractFileName(url: string, fallback: string): string {
  try {
    const pathname = new URL(url).pathname;
    const last = pathname.split("/").pop();
    if (last && last.includes(".")) return last;
  } catch {}
  return fallback;
}
