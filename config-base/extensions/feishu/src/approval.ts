import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuApprovalSchema, type FeishuApprovalParams } from "./approval-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function listDefinitions(client: Lark.Client) {
  const res = await (client as any).approval.approval.list({});
  if (res.code !== 0) throw new Error(res.msg);
  return {
    definitions: (res.data?.items ?? []).map((d: any) => ({
      approval_code: d.approval_code,
      approval_name: d.approval_name,
      status: d.status,
    })),
  };
}

async function getDefinition(client: Lark.Client, approvalCode: string) {
  const res = await (client as any).approval.approval.get({
    path: { approval_code: approvalCode },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    approval_name: res.data?.approval_name,
    status: res.data?.status,
    form: res.data?.form,
    node_list: res.data?.node_list,
  };
}

async function listInstances(client: Lark.Client, approvalCode: string, startTime?: string, endTime?: string) {
  const now = Date.now();
  const res = await (client as any).approval.instance.list({
    params: {
      approval_code: approvalCode,
      start_time: startTime || String(now - 30 * 24 * 3600 * 1000),
      end_time: endTime || String(now),
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    instances: (res.data?.instance_code_list ?? []),
    count: res.data?.instance_code_list?.length ?? 0,
  };
}

async function getInstance(client: Lark.Client, instanceId: string) {
  const res = await (client as any).approval.instance.get({
    params: { instance_id: instanceId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    approval_code: res.data?.approval_code,
    approval_name: res.data?.approval_name,
    status: res.data?.status,
    form: res.data?.form,
    task_list: res.data?.task_list,
    timeline: res.data?.timeline,
    start_time: res.data?.start_time,
    end_time: res.data?.end_time,
    user_id: res.data?.user_id,
  };
}

async function createInstance(client: Lark.Client, approvalCode: string, form: string, openId?: string) {
  const data: any = {
    approval_code: approvalCode,
    form,
  };
  if (openId) data.open_id = openId;

  const res = await (client as any).approval.instance.create({ data });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    instance_code: res.data?.instance_code,
  };
}

async function approveTask(client: Lark.Client, instanceId: string, taskId: string, comment?: string) {
  const res = await (client as any).approval.task.approve({
    data: {
      approval_code: "",
      instance_code: instanceId,
      task_id: taskId,
      comment: comment || "",
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true };
}

async function rejectTask(client: Lark.Client, instanceId: string, taskId: string, comment?: string) {
  const res = await (client as any).approval.task.reject({
    data: {
      approval_code: "",
      instance_code: instanceId,
      task_id: taskId,
      comment: comment || "",
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true };
}

// ============ Tool Registration ============

export function registerFeishuApprovalTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_approval",
      label: "Feishu Approval",
      description:
        "Feishu approval workflow operations. Actions: list_definitions, get_definition, list_instances, get_instance, create_instance, approve, reject",
      parameters: FeishuApprovalSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuApprovalParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "list_definitions":
              return json(await listDefinitions(client));
            case "get_definition":
              return json(await getDefinition(client, p.approval_code));
            case "list_instances":
              return json(await listInstances(client, p.approval_code, p.start_time, p.end_time));
            case "get_instance":
              return json(await getInstance(client, p.instance_id));
            case "create_instance":
              return json(await createInstance(client, p.approval_code, p.form, p.open_id));
            case "approve":
              return json(await approveTask(client, p.instance_id, p.task_id, p.comment));
            case "reject":
              return json(await rejectTask(client, p.instance_id, p.task_id, p.comment));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_approval" },
  );

  api.logger.info?.("feishu_approval: Registered feishu_approval tool");
}
