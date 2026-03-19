import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuAttendanceSchema, type FeishuAttendanceParams } from "./attendance-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function listGroups(client: Lark.Client, pageSize?: number) {
  const res = await (client as any).attendance.group.list({
    params: { page_size: Math.min(pageSize ?? 10, 50) },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    groups: (res.data?.group_list ?? []).map((g: any) => ({
      group_id: g.group_id,
      group_name: g.group_name,
      member_count: g.member_count,
    })),
    has_more: res.data?.has_more,
  };
}

async function getUserStats(client: Lark.Client, userIds: string[], startDate: string, endDate: string) {
  const res = await (client as any).attendance.userStatsData.query({
    data: {
      locale: "zh",
      stats_type: "month",
      start_date: startDate,
      end_date: endDate,
      user_ids: userIds,
    },
    params: { employee_type: "employee_id" },
  });
  // Fallback: some tenants use open_id
  if (res.code !== 0) {
    const res2 = await (client as any).attendance.userStatsData.query({
      data: {
        locale: "zh",
        stats_type: "month",
        start_date: startDate,
        end_date: endDate,
        user_ids: userIds,
      },
      params: { employee_type: "open_id" },
    });
    if (res2.code !== 0) throw new Error(res2.msg || res.msg);
    return { stats: res2.data?.user_datas ?? [] };
  }
  return { stats: res.data?.user_datas ?? [] };
}

async function getUserTasks(client: Lark.Client, userIds: string[], checkDateFrom: string, checkDateTo: string) {
  const res = await (client as any).attendance.userTask.query({
    data: {
      user_ids: userIds,
      check_date_from: checkDateFrom,
      check_date_to: checkDateTo,
    },
    params: { employee_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    tasks: (res.data?.user_task_results ?? []).map((t: any) => ({
      user_id: t.user_id,
      date: t.day,
      records: t.records?.map((r: any) => ({
        check_in_record_id: r.check_in_record_id,
        check_time: r.check_time,
        location_name: r.location_name,
        check_result: r.check_result,
      })),
    })),
  };
}

// ============ Tool Registration ============

export function registerFeishuAttendanceTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_attendance",
      label: "Feishu Attendance",
      description:
        "Feishu attendance/check-in operations. Actions: list_groups, get_user_stats, get_user_tasks",
      parameters: FeishuAttendanceSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuAttendanceParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "list_groups":
              return json(await listGroups(client, p.page_size));
            case "get_user_stats":
              return json(await getUserStats(client, p.user_ids, p.start_date, p.end_date));
            case "get_user_tasks":
              return json(await getUserTasks(client, p.user_ids, p.check_date_from, p.check_date_to));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_attendance" },
  );

  api.logger.info?.("feishu_attendance: Registered feishu_attendance tool");
}
