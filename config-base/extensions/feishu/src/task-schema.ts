import { Type, type Static } from "@sinclair/typebox";

export const FeishuTaskSchema = Type.Union([
  Type.Object({
    action: Type.Literal("create"),
    summary: Type.String({ description: "Task title/summary" }),
    description: Type.Optional(Type.String({ description: "Task description" })),
    due: Type.Optional(Type.String({ description: "Due date — Unix timestamp in seconds or ISO 8601 date" })),
    assignee_ids: Type.Optional(Type.Array(Type.String(), { description: "Array of open_id to assign" })),
  }),
  Type.Object({
    action: Type.Literal("get"),
    task_id: Type.String({ description: "Task GUID" }),
  }),
  Type.Object({
    action: Type.Literal("list"),
    page_size: Type.Optional(Type.Number({ description: "Number of results (default 20, max 50)" })),
  }),
  Type.Object({
    action: Type.Literal("complete"),
    task_id: Type.String({ description: "Task GUID to mark as complete" }),
  }),
  Type.Object({
    action: Type.Literal("uncomplete"),
    task_id: Type.String({ description: "Task GUID to reopen" }),
  }),
  Type.Object({
    action: Type.Literal("delete"),
    task_id: Type.String({ description: "Task GUID to delete" }),
  }),
  Type.Object({
    action: Type.Literal("add_members"),
    task_id: Type.String({ description: "Task GUID" }),
    member_ids: Type.Array(Type.String(), { description: "Array of open_id to add as assignees" }),
  }),
]);

export type FeishuTaskParams = Static<typeof FeishuTaskSchema>;
