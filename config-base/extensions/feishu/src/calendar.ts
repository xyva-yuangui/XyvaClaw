import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuCalendarSchema, type FeishuCalendarParams } from "./calendar-schema.js";
function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

function toTimestamp(v: string): string {
  if (/^\d+$/.test(v)) return v;
  const d = new Date(v);
  if (isNaN(d.getTime())) throw new Error(`Invalid time: ${v}`);
  return String(Math.floor(d.getTime() / 1000));
}

function isDateOnly(v: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(v);
}

// ============ Actions ============

async function listCalendars(client: Lark.Client) {
  const res = await (client as any).calendar.calendar.list({});
  if (res.code !== 0) throw new Error(res.msg);
  return {
    calendars: (res.data?.calendar_list ?? []).map((c: any) => ({
      calendar_id: c.calendar_id,
      summary: c.summary,
      description: c.description,
      type: c.type,
      role: c.role,
    })),
  };
}

async function listEvents(client: Lark.Client, calendarId: string, startTime?: string, endTime?: string) {
  const now = Math.floor(Date.now() / 1000);
  const params: any = {};
  if (startTime) params.start_time = toTimestamp(startTime);
  else params.start_time = String(now);
  if (endTime) params.end_time = toTimestamp(endTime);
  else params.end_time = String(now + 30 * 24 * 3600); // default 30 days

  const res = await (client as any).calendar.calendarEvent.list({
    path: { calendar_id: calendarId },
    params,
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    events: (res.data?.items ?? []).map((e: any) => ({
      event_id: e.event_id,
      summary: e.summary,
      description: e.description,
      start_time: e.start_time,
      end_time: e.end_time,
      status: e.status,
      location: e.location?.name,
      vchat: e.vchat?.meeting_url,
    })),
  };
}

async function createEvent(
  client: Lark.Client,
  calendarId: string,
  p: {
    summary: string;
    start_time: string;
    end_time: string;
    description?: string;
    location?: string;
    attendees?: string[];
    with_vc?: boolean;
  },
) {
  const isAllDay = isDateOnly(p.start_time) && isDateOnly(p.end_time);
  const startTime = isAllDay ? { date: p.start_time } : { timestamp: toTimestamp(p.start_time) };
  const endTime = isAllDay ? { date: p.end_time } : { timestamp: toTimestamp(p.end_time) };

  const data: any = {
    summary: p.summary,
    start_time: startTime,
    end_time: endTime,
  };
  if (p.description) data.description = p.description;
  if (p.location) data.location = { name: p.location };
  if (p.with_vc) data.vchat = { vc_type: "vc" };

  const res = await (client as any).calendar.calendarEvent.create({
    path: { calendar_id: calendarId },
    data,
    params: { user_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);

  const event = res.data?.event;

  // Add attendees if provided
  if (p.attendees && p.attendees.length > 0 && event?.event_id) {
    try {
      await (client as any).calendar.calendarEventAttendee.create({
        path: { calendar_id: calendarId, event_id: event.event_id },
        data: {
          attendees: p.attendees.map((id: string) => ({ type: "user", user_id: id })),
          need_notification: true,
        },
        params: { user_id_type: "open_id" },
      });
    } catch {
      // attendee add may fail due to permissions; event is still created
    }
  }

  return {
    event_id: event?.event_id,
    summary: event?.summary,
    start_time: event?.start_time,
    end_time: event?.end_time,
    vchat: event?.vchat?.meeting_url,
  };
}

async function deleteEvent(client: Lark.Client, calendarId: string, eventId: string) {
  const res = await (client as any).calendar.calendarEvent.delete({
    path: { calendar_id: calendarId, event_id: eventId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, event_id: eventId };
}

async function searchCalendars(client: Lark.Client, query: string) {
  const res = await (client as any).calendar.calendar.search({
    data: { query },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    calendars: (res.data?.items ?? []).map((c: any) => ({
      calendar_id: c.calendar_id,
      summary: c.summary,
      description: c.description,
      type: c.type,
    })),
  };
}

// ============ Tool Registration ============

export function registerFeishuCalendarTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_calendar",
      label: "Feishu Calendar",
      description:
        "Feishu calendar and event operations. Actions: list_calendars, list_events, create_event, delete_event, search_calendars",
      parameters: FeishuCalendarSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuCalendarParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "list_calendars":
              return json(await listCalendars(client));
            case "list_events":
              return json(await listEvents(client, p.calendar_id, p.start_time, p.end_time));
            case "create_event":
              return json(
                await createEvent(client, p.calendar_id, {
                  summary: p.summary,
                  start_time: p.start_time,
                  end_time: p.end_time,
                  description: p.description,
                  location: p.location,
                  attendees: p.attendees,
                  with_vc: p.with_vc,
                }),
              );
            case "delete_event":
              return json(await deleteEvent(client, p.calendar_id, p.event_id));
            case "search_calendars":
              return json(await searchCalendars(client, p.query));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_calendar" },
  );

  api.logger.info?.("feishu_calendar: Registered feishu_calendar tool");
}
