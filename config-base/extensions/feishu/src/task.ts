import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuTaskSchema, type FeishuTaskParams } from "./task-schema.js";

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

// ============ Actions ============

async function createTask(
  client: Lark.Client,
  summary: string,
  description?: string,
  due?: string,
  assigneeIds?: string[],
) {
  const data: any = { summary };
  if (description) data.description = description;
  if (due) data.due = { timestamp: toTimestamp(due), is_all_day: false };
  if (assigneeIds && assigneeIds.length > 0) {
    data.members = assigneeIds.map((id: string) => ({ id, type: "user", role: "assignee" }));
  }

  const res = await (client as any).task.v2.task.create({ data });
  if (res.code !== 0) throw new Error(res.msg);
  const t = res.data?.task;
  return {
    task_id: t?.guid,
    summary: t?.summary,
    due: t?.due,
    completed_at: t?.completed_at,
    url: t?.url,
  };
}

async function getTask(client: Lark.Client, taskId: string) {
  const res = await (client as any).task.v2.task.get({
    path: { task_guid: taskId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  const t = res.data?.task;
  return {
    task_id: t?.guid,
    summary: t?.summary,
    description: t?.description,
    due: t?.due,
    completed_at: t?.completed_at,
    members: t?.members,
    url: t?.url,
    created_at: t?.created_at,
    updated_at: t?.updated_at,
  };
}

async function listTasks(client: Lark.Client, pageSize?: number) {
  const res = await (client as any).task.v2.task.list({
    params: { page_size: Math.min(pageSize ?? 20, 50) },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    tasks: (res.data?.items ?? []).map((t: any) => ({
      task_id: t.guid,
      summary: t.summary,
      due: t.due,
      completed_at: t.completed_at,
      url: t.url,
    })),
    has_more: res.data?.has_more,
  };
}

async function completeTask(client: Lark.Client, taskId: string) {
  const res = await (client as any).task.v2.task.complete({
    path: { task_guid: taskId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, task_id: taskId };
}

async function uncompleteTask(client: Lark.Client, taskId: string) {
  const res = await (client as any).task.v2.task.uncomplete({
    path: { task_guid: taskId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, task_id: taskId };
}

async function deleteTask(client: Lark.Client, taskId: string) {
  const res = await (client as any).task.v2.task.delete({
    path: { task_guid: taskId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, task_id: taskId };
}

async function addTaskMembers(client: Lark.Client, taskId: string, memberIds: string[]) {
  const res = await (client as any).task.v2.task.addMembers({
    path: { task_guid: taskId },
    data: {
      members: memberIds.map((id: string) => ({ id, type: "user", role: "assignee" })),
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, task_id: taskId };
}

// ============ Tool Registration ============

export function registerFeishuTaskTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_task",
      label: "Feishu Task",
      description:
        "Feishu task management. Actions: create, get, list, complete, uncomplete, delete, add_members",
      parameters: FeishuTaskSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuTaskParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "create":
              return json(await createTask(client, p.summary, p.description, p.due, p.assignee_ids));
            case "get":
              return json(await getTask(client, p.task_id));
            case "list":
              return json(await listTasks(client, p.page_size));
            case "complete":
              return json(await completeTask(client, p.task_id));
            case "uncomplete":
              return json(await uncompleteTask(client, p.task_id));
            case "delete":
              return json(await deleteTask(client, p.task_id));
            case "add_members":
              return json(await addTaskMembers(client, p.task_id, p.member_ids));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_task" },
  );

  api.logger.info?.("feishu_task: Registered feishu_task tool");
}
