import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuSearchSchema, type FeishuSearchParams } from "./search-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function searchMessages(client: Lark.Client, query: string, chatId?: string, pageSize?: number) {
  const params: any = {
    query,
    page_size: Math.min(pageSize ?? 20, 50),
    message_type: "text",
  };
  if (chatId) params.chat_id = chatId;

  const res = await (client as any).im.message.search({ params });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    messages: (res.data?.items ?? []).map((m: any) => ({
      message_id: m.message_id,
      chat_id: m.chat_id,
      msg_type: m.msg_type,
      content: m.body?.content,
      sender_id: m.sender?.id,
      create_time: m.create_time,
    })),
    has_more: res.data?.has_more,
  };
}

async function searchDocs(client: Lark.Client, query: string, pageSize?: number) {
  const res = await (client as any).suite.search.message({
    data: {
      query,
      search_resource_type: "doc",
    },
    params: {
      page_size: Math.min(pageSize ?? 20, 50),
    },
  });

  // Fallback: try drive search if suite search not available
  if (res.code !== 0) {
    const driveRes = await (client as any).drive.file.list({
      params: {
        page_size: Math.min(pageSize ?? 20, 50),
        order_by: "EditedTime",
        direction: "DESC",
      },
    });
    if (driveRes.code !== 0) throw new Error(driveRes.msg || res.msg);
    return {
      docs: (driveRes.data?.files ?? []).map((f: any) => ({
        token: f.token,
        name: f.name,
        type: f.type,
        url: f.url,
        owner_id: f.owner_id,
        created_time: f.created_time,
        modified_time: f.modified_time,
      })),
      note: "Used drive file list as fallback (suite search unavailable). Results are recent files, not search results.",
    };
  }

  return {
    docs: (res.data?.items ?? []).map((d: any) => ({
      token: d.id,
      title: d.title,
      type: d.type,
      url: d.url,
      owner: d.owner,
      create_time: d.create_time,
      update_time: d.update_time,
    })),
    has_more: res.data?.has_more,
  };
}

async function searchChats(client: Lark.Client, query: string, pageSize?: number) {
  const res = await (client as any).im.chat.search({
    params: {
      query,
      page_size: Math.min(pageSize ?? 20, 50),
    },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    chats: (res.data?.items ?? []).map((c: any) => ({
      chat_id: c.chat_id,
      name: c.name,
      description: c.description,
      owner_id: c.owner_id,
      member_count: c.user_count,
    })),
    has_more: res.data?.has_more,
  };
}

// ============ Tool Registration ============

export function registerFeishuSearchTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_search",
      label: "Feishu Search",
      description:
        "Search Feishu messages, documents, and group chats. Actions: search_messages, search_docs, search_chats",
      parameters: FeishuSearchSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuSearchParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "search_messages":
              return json(await searchMessages(client, p.query, p.chat_id, p.page_size));
            case "search_docs":
              return json(await searchDocs(client, p.query, p.page_size));
            case "search_chats":
              return json(await searchChats(client, p.query, p.page_size));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_search" },
  );

  api.logger.info?.("feishu_search: Registered feishu_search tool");
}
