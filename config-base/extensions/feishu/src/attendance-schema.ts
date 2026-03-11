import { Type, type Static } from "@sinclair/typebox";

export const FeishuAttendanceSchema = Type.Union([
  Type.Object({
    action: Type.Literal("list_groups"),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 10)" })),
  }),
  Type.Object({
    action: Type.Literal("get_user_stats"),
    user_ids: Type.Array(Type.String(), { description: "Array of open_id to query" }),
    start_date: Type.String({ description: "Start date YYYYMMDD" }),
    end_date: Type.String({ description: "End date YYYYMMDD" }),
  }),
  Type.Object({
    action: Type.Literal("get_user_tasks"),
    user_ids: Type.Array(Type.String(), { description: "Array of open_id to query" }),
    check_date_from: Type.String({ description: "Start date YYYYMMDD" }),
    check_date_to: Type.String({ description: "End date YYYYMMDD" }),
  }),
]);

export type FeishuAttendanceParams = Static<typeof FeishuAttendanceSchema>;
