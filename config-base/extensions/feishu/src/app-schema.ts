import { Type, type Static } from "@sinclair/typebox";

export const FeishuAppSchema = Type.Union([
  Type.Object({
    action: Type.Literal("list_apps"),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20)" })),
    status: Type.Optional(Type.Number({ description: "App status filter: 0=all, 1=enabled, 2=disabled, 3=unreviewed" })),
  }),
  Type.Object({
    action: Type.Literal("get_app"),
    app_id: Type.String({ description: "Application ID" }),
  }),
  Type.Object({
    action: Type.Literal("check_visibility"),
    app_id: Type.String({ description: "Application ID" }),
    user_ids: Type.Optional(Type.Array(Type.String(), { description: "Array of open_id to check visibility for" })),
  }),
  Type.Object({
    action: Type.Literal("list_app_versions"),
    app_id: Type.String({ description: "Application ID" }),
  }),
]);

export type FeishuAppParams = Static<typeof FeishuAppSchema>;
