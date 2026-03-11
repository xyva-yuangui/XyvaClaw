import { Type, type Static } from "@sinclair/typebox";

export const FeishuVcSchema = Type.Union([
  Type.Object({
    action: Type.Literal("create_meeting"),
    topic: Type.String({ description: "Meeting topic/title" }),
    start_time: Type.Optional(Type.String({ description: "Start time Unix timestamp in seconds (omit for immediate)" })),
    end_time: Type.Optional(Type.String({ description: "End time Unix timestamp in seconds" })),
    invitee_ids: Type.Optional(Type.Array(Type.String(), { description: "Array of open_id to invite" })),
  }),
  Type.Object({
    action: Type.Literal("get_meeting"),
    meeting_id: Type.String({ description: "Meeting ID" }),
  }),
  Type.Object({
    action: Type.Literal("list_meetings"),
    start_time: Type.Optional(Type.String({ description: "Start time Unix timestamp in seconds" })),
    end_time: Type.Optional(Type.String({ description: "End time Unix timestamp in seconds" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page (default 20)" })),
  }),
  Type.Object({
    action: Type.Literal("end_meeting"),
    meeting_id: Type.String({ description: "Meeting ID to end" }),
  }),
]);

export type FeishuVcParams = Static<typeof FeishuVcSchema>;
