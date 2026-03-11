import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuAppSchema, type FeishuAppParams } from "./app-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function listApps(client: Lark.Client, pageSize?: number, status?: number) {
  const params: any = { page_size: Math.min(pageSize ?? 20, 50) };
  if (status !== undefined) params.status = status;

  const res = await (client as any).application.application.list({ params });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    apps: (res.data?.app_list ?? []).map((a: any) => ({
      app_id: a.app_id,
      name: a.app_name,
      description: a.description,
      status: a.status,
      app_scene_type: a.app_scene_type,
    })),
    has_more: res.data?.has_more,
  };
}

async function getApp(client: Lark.Client, appId: string) {
  const res = await (client as any).application.application.get({
    path: { app_id: appId },
    params: { lang: "zh_cn" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  const a = res.data?.app;
  return {
    app_id: a?.app_id,
    name: a?.app_name,
    description: a?.description,
    status: a?.status,
    primary_language: a?.primary_language,
    owner: a?.owner,
    scopes: a?.app_usage?.scopes,
  };
}

async function checkVisibility(client: Lark.Client, appId: string, userIds?: string[]) {
  const res = await (client as any).application.applicationVisibility.list({
    path: { app_id: appId },
    params: { user_id_type: "open_id", page_size: 50 },
  });
  if (res.code !== 0) throw new Error(res.msg);
  const allVisible = (res.data?.items ?? []).map((v: any) => v.user_id);
  if (userIds && userIds.length > 0) {
    const visibleSet = new Set(allVisible);
    return {
      results: userIds.map((id: string) => ({ user_id: id, visible: visibleSet.has(id) })),
    };
  }
  return {
    visible_users: allVisible,
    has_more: res.data?.has_more,
  };
}

async function listAppVersions(client: Lark.Client, appId: string) {
  const res = await (client as any).application.applicationAppVersion.list({
    path: { app_id: appId },
    params: { page_size: 20, lang: "zh_cn" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    versions: (res.data?.items ?? []).map((v: any) => ({
      version_id: v.version_id,
      version: v.version,
      status: v.status,
      create_time: v.create_time,
      publish_time: v.publish_time,
    })),
    has_more: res.data?.has_more,
  };
}

// ============ Tool Registration ============

export function registerFeishuAppTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_app",
      label: "Feishu App",
      description:
        "Feishu application/mini-program management. Actions: list_apps, get_app, check_visibility, list_app_versions",
      parameters: FeishuAppSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuAppParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "list_apps":
              return json(await listApps(client, p.page_size, p.status));
            case "get_app":
              return json(await getApp(client, p.app_id));
            case "check_visibility":
              return json(await checkVisibility(client, p.app_id, p.user_ids));
            case "list_app_versions":
              return json(await listAppVersions(client, p.app_id));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_app" },
  );

  api.logger.info?.("feishu_app: Registered feishu_app tool");
}
