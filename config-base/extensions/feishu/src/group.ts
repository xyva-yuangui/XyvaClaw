import type * as Lark from "@larksuiteoapi/node-sdk";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuGroupSchema, type FeishuGroupParams } from "./group-schema.js";

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

// ============ Actions ============

async function listChats(client: Lark.Client, pageSize?: number) {
  const res = await (client as any).im.chat.list({
    params: { page_size: Math.min(pageSize ?? 20, 100) },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    chats: (res.data?.items ?? []).map((c: any) => ({
      chat_id: c.chat_id,
      name: c.name,
      description: c.description,
      owner_id: c.owner_id,
      chat_mode: c.chat_mode,
      member_count: c.user_count,
    })),
    has_more: res.data?.has_more,
  };
}

async function getChat(client: Lark.Client, chatId: string) {
  const res = await (client as any).im.chat.get({
    path: { chat_id: chatId },
    params: { user_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    chat_id: res.data?.chat_id,
    name: res.data?.name,
    description: res.data?.description,
    owner_id: res.data?.owner_id,
    chat_mode: res.data?.chat_mode,
    member_count: res.data?.user_count,
    external: res.data?.external,
  };
}

async function createChat(
  client: Lark.Client,
  name: string,
  description?: string,
  ownerId?: string,
  memberIds?: string[],
) {
  const data: any = { name };
  if (description) data.description = description;
  if (ownerId) data.owner_id = ownerId;
  if (memberIds && memberIds.length > 0) {
    data.user_id_list = memberIds;
  }

  const res = await (client as any).im.chat.create({
    data,
    params: { user_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    chat_id: res.data?.chat_id,
    name: res.data?.name,
  };
}

async function updateChat(client: Lark.Client, chatId: string, name?: string, description?: string) {
  const data: any = {};
  if (name) data.name = name;
  if (description) data.description = description;

  const res = await (client as any).im.chat.update({
    path: { chat_id: chatId },
    data,
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, chat_id: chatId };
}

async function addMembers(client: Lark.Client, chatId: string, memberIds: string[]) {
  const res = await (client as any).im.chatMembers.create({
    path: { chat_id: chatId },
    data: { id_list: memberIds },
    params: { member_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    success: true,
    invalid_ids: res.data?.invalid_id_list ?? [],
    not_existed_ids: res.data?.not_existed_id_list ?? [],
  };
}

async function removeMembers(client: Lark.Client, chatId: string, memberIds: string[]) {
  const res = await (client as any).im.chatMembers.delete({
    path: { chat_id: chatId },
    data: { id_list: memberIds },
    params: { member_id_type: "open_id" },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    success: true,
    invalid_ids: res.data?.invalid_id_list ?? [],
  };
}

async function listMembers(client: Lark.Client, chatId: string) {
  const res = await (client as any).im.chatMembers.get({
    path: { chat_id: chatId },
    params: { member_id_type: "open_id", page_size: 100 },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return {
    members: (res.data?.items ?? []).map((m: any) => ({
      member_id: m.member_id,
      name: m.name,
      member_id_type: m.member_id_type,
    })),
    has_more: res.data?.has_more,
  };
}

async function disbandChat(client: Lark.Client, chatId: string) {
  const res = await (client as any).im.chat.delete({
    path: { chat_id: chatId },
  });
  if (res.code !== 0) throw new Error(res.msg);
  return { success: true, chat_id: chatId };
}

// ============ Tool Registration ============

export function registerFeishuGroupTools(api: OpenClawPluginApi) {
  if (!api.config) return;
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) return;

  const firstAccount = accounts[0];
  const getClient = () => createFeishuClient(firstAccount);

  api.registerTool(
    {
      name: "feishu_group",
      label: "Feishu Group",
      description:
        "Feishu group chat management. Actions: list_chats, get_chat, create_chat, update_chat, add_members, remove_members, list_members, disband_chat",
      parameters: FeishuGroupSchema,
      async execute(_toolCallId, params) {
        const p = params as FeishuGroupParams;
        try {
          const client = getClient();
          switch (p.action) {
            case "list_chats":
              return json(await listChats(client, p.page_size));
            case "get_chat":
              return json(await getChat(client, p.chat_id));
            case "create_chat":
              return json(await createChat(client, p.name, p.description, p.owner_id, p.member_ids));
            case "update_chat":
              return json(await updateChat(client, p.chat_id, p.name, p.description));
            case "add_members":
              return json(await addMembers(client, p.chat_id, p.member_ids));
            case "remove_members":
              return json(await removeMembers(client, p.chat_id, p.member_ids));
            case "list_members":
              return json(await listMembers(client, p.chat_id));
            case "disband_chat":
              return json(await disbandChat(client, p.chat_id));
            default:
              return json({ error: `Unknown action: ${(p as any).action}` });
          }
        } catch (err) {
          return json({ error: err instanceof Error ? err.message : String(err) });
        }
      },
    },
    { name: "feishu_group" },
  );

  api.logger.info?.("feishu_group: Registered feishu_group tool");
}
