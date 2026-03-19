import { Type, type Static } from "@sinclair/typebox";

export const FeishuWebhookSchema = Type.Object({
  action: Type.Literal("send"),
  webhook_url: Type.String({ description: "Feishu incoming webhook URL (https://open.feishu.cn/open-apis/bot/v2/hook/...)" }),
  msg_type: Type.Optional(Type.String({ description: "Message type: text (default), post, interactive" })),
  content: Type.String({ description: "Message content. For text: plain text string. For post/interactive: JSON string." }),
});

export type FeishuWebhookParams = Static<typeof FeishuWebhookSchema>;
