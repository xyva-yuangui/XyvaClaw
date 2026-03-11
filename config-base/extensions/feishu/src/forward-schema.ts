import { Type, type Static } from "@sinclair/typebox";

export const FeishuForwardSchema = Type.Union([
  Type.Object({
    action: Type.Literal("forward"),
    message_id: Type.String({ description: "Message ID to forward" }),
    target: Type.String({ description: "Target: 'user:open_id' or 'chat:chat_id'" }),
  }),
  Type.Object({
    action: Type.Literal("merge_forward"),
    message_ids: Type.Array(Type.String(), { description: "Array of message IDs to merge forward" }),
    target: Type.String({ description: "Target: 'user:open_id' or 'chat:chat_id'" }),
  }),
]);

export type FeishuForwardParams = Static<typeof FeishuForwardSchema>;
