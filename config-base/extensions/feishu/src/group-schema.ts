import { Type, type Static } from "@sinclair/typebox";

export const FeishuGroupSchema = Type.Union([
  Type.Object({
    action: Type.Literal("list_chats"),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20, max 100)" })),
  }),
  Type.Object({
    action: Type.Literal("get_chat"),
    chat_id: Type.String({ description: "Group chat ID" }),
  }),
  Type.Object({
    action: Type.Literal("create_chat"),
    name: Type.String({ description: "Group chat name" }),
    description: Type.Optional(Type.String({ description: "Group description" })),
    owner_id: Type.Optional(Type.String({ description: "Owner open_id (defaults to bot)" })),
    member_ids: Type.Optional(Type.Array(Type.String(), { description: "Array of open_id to add as members" })),
  }),
  Type.Object({
    action: Type.Literal("update_chat"),
    chat_id: Type.String({ description: "Group chat ID" }),
    name: Type.Optional(Type.String({ description: "New group name" })),
    description: Type.Optional(Type.String({ description: "New group description" })),
  }),
  Type.Object({
    action: Type.Literal("add_members"),
    chat_id: Type.String({ description: "Group chat ID" }),
    member_ids: Type.Array(Type.String(), { description: "Array of open_id to add" }),
  }),
  Type.Object({
    action: Type.Literal("remove_members"),
    chat_id: Type.String({ description: "Group chat ID" }),
    member_ids: Type.Array(Type.String(), { description: "Array of open_id to remove" }),
  }),
  Type.Object({
    action: Type.Literal("list_members"),
    chat_id: Type.String({ description: "Group chat ID" }),
  }),
  Type.Object({
    action: Type.Literal("disband_chat"),
    chat_id: Type.String({ description: "Group chat ID to disband/delete" }),
  }),
]);

export type FeishuGroupParams = Static<typeof FeishuGroupSchema>;
