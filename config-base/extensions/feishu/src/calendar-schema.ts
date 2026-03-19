import { Type, type Static } from "@sinclair/typebox";

export const FeishuCalendarSchema = Type.Union([
  Type.Object({
    action: Type.Literal("list_calendars"),
  }),
  Type.Object({
    action: Type.Literal("list_events"),
    calendar_id: Type.String({ description: "Calendar ID (use 'primary' for the app's primary calendar)" }),
    start_time: Type.Optional(Type.String({ description: "Start time in ISO 8601 or Unix timestamp (seconds)" })),
    end_time: Type.Optional(Type.String({ description: "End time in ISO 8601 or Unix timestamp (seconds)" })),
  }),
  Type.Object({
    action: Type.Literal("create_event"),
    calendar_id: Type.String({ description: "Calendar ID" }),
    summary: Type.String({ description: "Event title" }),
    start_time: Type.String({ description: "Start time — Unix timestamp in seconds, or date string YYYY-MM-DD for all-day" }),
    end_time: Type.String({ description: "End time — Unix timestamp in seconds, or date string YYYY-MM-DD for all-day" }),
    description: Type.Optional(Type.String({ description: "Event description" })),
    location: Type.Optional(Type.String({ description: "Event location name" })),
    attendees: Type.Optional(Type.Array(Type.String(), { description: "Array of open_id strings to invite" })),
    with_vc: Type.Optional(Type.Boolean({ description: "Create with video conference link (default false)" })),
  }),
  Type.Object({
    action: Type.Literal("delete_event"),
    calendar_id: Type.String({ description: "Calendar ID" }),
    event_id: Type.String({ description: "Event ID" }),
  }),
  Type.Object({
    action: Type.Literal("search_calendars"),
    query: Type.String({ description: "Search keyword" }),
  }),
]);

export type FeishuCalendarParams = Static<typeof FeishuCalendarSchema>;
