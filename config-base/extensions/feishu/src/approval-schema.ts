import { Type, type Static } from "@sinclair/typebox";

export const FeishuApprovalSchema = Type.Union([
  Type.Object({
    action: Type.Literal("list_definitions"),
  }),
  Type.Object({
    action: Type.Literal("get_definition"),
    approval_code: Type.String({ description: "Approval definition code" }),
  }),
  Type.Object({
    action: Type.Literal("list_instances"),
    approval_code: Type.String({ description: "Approval definition code" }),
    start_time: Type.Optional(Type.String({ description: "Start time Unix timestamp in ms" })),
    end_time: Type.Optional(Type.String({ description: "End time Unix timestamp in ms" })),
  }),
  Type.Object({
    action: Type.Literal("get_instance"),
    instance_id: Type.String({ description: "Approval instance ID" }),
  }),
  Type.Object({
    action: Type.Literal("create_instance"),
    approval_code: Type.String({ description: "Approval definition code" }),
    form: Type.String({ description: "Form data as JSON string (keys match the approval form field names)" }),
    open_id: Type.Optional(Type.String({ description: "Applicant open_id (defaults to bot)" })),
  }),
  Type.Object({
    action: Type.Literal("approve"),
    instance_id: Type.String({ description: "Instance ID" }),
    task_id: Type.String({ description: "Task ID of the approval task" }),
    comment: Type.Optional(Type.String({ description: "Approval comment" })),
  }),
  Type.Object({
    action: Type.Literal("reject"),
    instance_id: Type.String({ description: "Instance ID" }),
    task_id: Type.String({ description: "Task ID of the approval task" }),
    comment: Type.Optional(Type.String({ description: "Rejection comment" })),
  }),
]);

export type FeishuApprovalParams = Static<typeof FeishuApprovalSchema>;
