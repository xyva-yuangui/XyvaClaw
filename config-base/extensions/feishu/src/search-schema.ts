import { Type, type Static } from "@sinclair/typebox";

export const FeishuSearchSchema = Type.Union([
  Type.Object({
    action: Type.Literal("search_messages"),
    query: Type.String({ description: "Search keyword for messages" }),
    chat_id: Type.Optional(Type.String({ description: "Limit search to a specific chat (group or DM)" })),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20, max 50)" })),
  }),
  Type.Object({
    action: Type.Literal("search_docs"),
    query: Type.String({ description: "Search keyword for documents (docx, sheets, slides, etc.)" }),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20, max 50)" })),
  }),
  Type.Object({
    action: Type.Literal("search_chats"),
    query: Type.String({ description: "Search keyword for group chats" }),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20, max 50)" })),
  }),
]);

export type FeishuSearchParams = Static<typeof FeishuSearchSchema>;
