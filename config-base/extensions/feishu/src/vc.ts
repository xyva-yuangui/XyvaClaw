import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuVcSchema, type FeishuVcParams } from "./vc-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function createMeeting(
  client: Lark.Client,
  topic: string,
  startTime?: string,
  endTime?: string,
  inviteeIds?: string[],
) {
  const now = String(Math.floor(Date.now() / 1000));
  const res = await (client as any).vc.reserve.apply({
    data: {
      end_time: endTime || String(Number(startTime || now) + 3600),
      meeting_settings: {
        topic,
        ...(inviteeIds && inviteeIds.length > 0
          ? {
              action_permissions: inviteeIds.map((id: string) => ({
                permission: 1,
                permission_checkers: { check_field: 1, check_mode: 1, check_list: [id] },
              })),
            }
          : {}),
      },
    },
    params: { user_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  const r = res.data?.reserve;
  return {
    reserve_id: r?.id,
    meeting_no: r?.meeting_no,
    url: r?.url,
    topic: topic,
  };
}

async function getMeeting(client: Lark.Client, meetingId: string) {
  const res = await (client as any).vc.meeting.get({
    path: { meeting_id: meetingId },
    params: { with_participants: true, user_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  const m = res.data?.meeting;
  return {
    meeting_id: m?.id,
    topic: m?.topic,
    meeting_no: m?.meeting_no,
    url: m?.url,
    start_time: m?.start_time,
    end_time: m?.end_time,
    status: m?.status,
    host_user: m?.host_user,
    participant_count: m?.participant_count,
  };
}

async function listMeetings(client: Lark.Client, startTime?: string, endTime?: string, pageSize?: number) {
  const now = Math.floor(Date.now() / 1000);
  const res = await (client as any).vc.meeting.list({
    params: {
      start_time: startTime || String(now - 7 * 24 * 3600),
      end_time: endTime || String(now),
      page_size: Math.min(pageSize ?? 20, 50),
      meeting_status: 1,
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    meetings: (res.data?.meeting_list ?? []).map((m: any) => ({
      meeting_id: m.id,
      topic: m.topic,
      meeting_no: m.meeting_no,
      start_time: m.start_time,
      end_time: m.end_time,
      status: m.status,
      host_user: m.host_user,
    })),
    has_more: res.data?.has_more,
  };
}

async function endMeeting(client: Lark.Client, meetingId: string) {
  const res = await (client as any).vc.meeting.end({
    path: { meeting_id: meetingId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, meeting_id: meetingId };
}

// ============ Tool Registration ============

export function registerFeishuVcTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_vc",
      label: "Feishu Video Conference",
      description:
        "Feishu video conference operations. Actions: create_meeting, get_meeting, list_meetings, end_meeting",
      parameters: FeishuVcSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuVcParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "create_meeting":
              return json(await createMeeting(client, p.topic, p.start_time, p.end_time, p.invitee_ids));
            case "get_meeting":
              return json(await getMeeting(client, p.meeting_id));
            case "list_meetings":
              return json(await listMeetings(client, p.start_time, p.end_time, p.page_size));
            case "end_meeting":
              return json(await endMeeting(client, p.meeting_id));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_vc" },
  );

  api.logger.info?.("feishu_vc: Registered feishu_vc tool");
}
