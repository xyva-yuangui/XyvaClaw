import { Readable } from "stream";
import { join } from "path";
import { homedir } from "os";
import { execFile } from "child_process";
import { promisify } from "util";
import type * as Lark from "@larksuiteoapi/node-sdk";
import { Type } from "@sinclair/typebox";
import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { listEnabledFeishuAccounts } from "./accounts.js";
import { createFeishuClient } from "./client.js";
import { FeishuDocSchema, type FeishuDocParams } from "./doc-schema.js";
import { getFeishuRuntime } from "./runtime.js";
import { resolveToolsConfig } from "./tools-config.js";
import { insertBlocksInBatches } from "./docx-batch-insert.js";

const execFileAsync = promisify(execFile);

// ============ Helpers ============

function json(data: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

/** Extract image URLs from markdown content */
function extractImageUrls(markdown: string): string[] {
  const regex = /!\[[^\]]*\]\(([^)]+)\)/g;
  const urls: string[] = [];
  let match;
  while ((match = regex.exec(markdown)) !== null) {
    const url = match[1].trim();
    if (url.startsWith("http://") || url.startsWith("https://")) {
      urls.push(url);
    }
  }
  return urls;
}

function formatMarkdownForDoc(markdown: string, titleHint?: string): string {
  const trimmed = markdown.trim();
  if (!trimmed) return trimmed;

  const compact = trimmed.replace(/\n{3,}/g, "\n\n");
  if (/^#{1,6}\s/m.test(compact)) {
    return compact;
  }

  const title = (titleHint || "文档内容").trim();
  return `# ${title}\n\n${compact}`;
}

function buildIllustrationPrompt(markdown: string, customPrompt?: string): string {
  if (customPrompt?.trim()) return customPrompt.trim();
  const snippet = markdown
    .replace(/```[\s\S]*?```/g, "")
    .replace(/!\[[^\]]*\]\([^)]+\)/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 280);
  return `为以下文档生成一张专业、清晰、信息表达强的配图，16:9 横图，无水印，无文字乱码：${snippet}`;
}

async function generateIllustrationViaQwen(prompt: string, apiKey?: string): Promise<string | null> {
  const scriptPath = join(homedir(), ".openclaw/workspace/skills/qwen-image/scripts/generate_image.py");
  const args = ["run", scriptPath, "--prompt", prompt, "--model", "wan2.6-t2i", "--size", "1664*928"];
  const normalizedApiKey = String(apiKey ?? "").trim();
  if (normalizedApiKey) {
    args.push("--api-key", normalizedApiKey);
  }
  const { stdout } = await execFileAsync("uv", args, { maxBuffer: 8 * 1024 * 1024 });
  const line = stdout
    .split(/\r?\n/)
    .map((s) => s.trim())
    .find((s) => s.startsWith("MEDIA_URL:"));
  if (!line) return null;
  const url = line.replace("MEDIA_URL:", "").trim();
  return url.startsWith("http://") || url.startsWith("https://") ? url : null;
}

async function enhanceMarkdownForDoc(params: {
  markdown: string;
  titleHint?: string;
  autoIllustrate?: boolean;
  imagePrompt?: string;
  illustrationApiKey?: string;
}): Promise<{ markdown: string; generatedImageUrl?: string; generated: boolean; warning?: string }> {
  const base = formatMarkdownForDoc(params.markdown, params.titleHint);
  const hasImage = extractImageUrls(base).length > 0;
  const shouldGenerate = params.autoIllustrate ?? true;

  if (hasImage || !shouldGenerate) {
    return { markdown: base, generated: false };
  }

  try {
    const prompt = buildIllustrationPrompt(base, params.imagePrompt);
    const url = await generateIllustrationViaQwen(prompt, params.illustrationApiKey);
    if (!url) {
      return { markdown: base, generated: false, warning: "Qwen illustration url not returned." };
    }
    const withImage = `${base}\n\n## 配图\n\n![文档配图](${url})\n`;
    return { markdown: withImage, generated: true, generatedImageUrl: url };
  } catch (err) {
    return {
      markdown: base,
      generated: false,
      warning: `Qwen illustration failed: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

const BLOCK_TYPE_NAMES: Record<number, string> = {
  1: "Page",
  2: "Text",
  3: "Heading1",
  4: "Heading2",
  5: "Heading3",
  12: "Bullet",
  13: "Ordered",
  14: "Code",
  15: "Quote",
  17: "Todo",
  18: "Bitable",
  21: "Diagram",
  22: "Divider",
  23: "File",
  27: "Image",
  30: "Sheet",
  31: "Table",
  32: "TableCell",
};

// Block types that cannot be created via documentBlockChildren.create API
const UNSUPPORTED_CREATE_TYPES = new Set([31, 32]);

/** Clean blocks for insertion (remove unsupported types and read-only fields) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SDK block types
function cleanBlocksForInsert(blocks: any[]): { cleaned: any[]; skipped: string[] } {
  const skipped: string[] = [];
  const cleaned = blocks
    .filter((block) => {
      if (UNSUPPORTED_CREATE_TYPES.has(block.block_type)) {
        const typeName = BLOCK_TYPE_NAMES[block.block_type] || `type_${block.block_type}`;
        skipped.push(typeName);
        return false;
      }
      return true;
    })
    .map((block) => {
      // Strip read-only fields that the create API rejects (99992402 field validation)
      const { block_id: _bid, parent_id: _pid, children: _ch, ...rest } = block;
      if (rest.block_type === 31 && rest.table?.merge_info) {
        const { merge_info: _merge_info, ...tableRest } = rest.table;
        return { ...rest, table: tableRest };
      }
      return rest;
    });
  return { cleaned, skipped };
}

/** Check if any blocks contain table types that require the Descendant API */
function hasTableBlocks(blocks: any[]): boolean {
  return blocks.some((b) => b.block_type === 31 || b.block_type === 32);
}

// ============ Core Functions ============

async function convertMarkdown(client: Lark.Client, markdown: string) {
  const res = await client.docx.document.convert({
    data: { content_type: "markdown", content: markdown },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }
  return {
    blocks: res.data?.blocks ?? [],
    firstLevelBlockIds: res.data?.first_level_block_ids ?? [],
  };
}

function sortBlocksByFirstLevel(blocks: any[], firstLevelIds: string[]): any[] {
  if (!firstLevelIds || firstLevelIds.length === 0) return blocks;
  const sorted = firstLevelIds.map((id) => blocks.find((b) => b.block_id === id)).filter(Boolean);
  const sortedIds = new Set(firstLevelIds);
  const remaining = blocks.filter((b) => !sortedIds.has(b.block_id));
  return [...sorted, ...remaining];
}

/* eslint-disable @typescript-eslint/no-explicit-any -- SDK block types */
async function insertBlocks(
  client: Lark.Client,
  docToken: string,
  blocks: any[],
  parentBlockId?: string,
): Promise<{ children: any[]; skipped: string[] }> {
  /* eslint-enable @typescript-eslint/no-explicit-any */
  const { cleaned, skipped } = cleanBlocksForInsert(blocks);
  const blockId = parentBlockId ?? docToken;

  if (cleaned.length === 0) {
    return { children: [], skipped };
  }

  const res = await client.docx.documentBlockChildren.create({
    path: { document_id: docToken, block_id: blockId },
    data: { children: cleaned },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }
  return { children: res.data?.children ?? [], skipped };
}

async function clearDocumentContent(client: Lark.Client, docToken: string) {
  const existing = await client.docx.documentBlock.list({
    path: { document_id: docToken },
  });
  if (existing.code !== 0) {
    throw new Error(existing.msg);
  }

  const childIds =
    existing.data?.items
      ?.filter((b) => b.parent_id === docToken && b.block_type !== 1)
      .map((b) => b.block_id) ?? [];

  if (childIds.length > 0) {
    const res = await client.docx.documentBlockChildren.batchDelete({
      path: { document_id: docToken, block_id: docToken },
      data: { start_index: 0, end_index: childIds.length },
    });
    if (res.code !== 0) {
      throw new Error(res.msg);
    }
  }

  return childIds.length;
}

async function uploadImageToDocx(
  client: Lark.Client,
  blockId: string,
  imageBuffer: Buffer,
  fileName: string,
): Promise<string> {
  const res = await client.drive.media.uploadAll({
    data: {
      file_name: fileName,
      parent_type: "docx_image",
      parent_node: blockId,
      size: imageBuffer.length,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- SDK stream type
      file: Readable.from(imageBuffer) as any,
    },
  });

  const fileToken = res?.file_token;
  if (!fileToken) {
    throw new Error("Image upload failed: no file_token returned");
  }
  return fileToken;
}

async function downloadImage(url: string, maxBytes: number): Promise<Buffer> {
  const fetched = await getFeishuRuntime().channel.media.fetchRemoteMedia({ url, maxBytes });
  return fetched.buffer;
}

/* eslint-disable @typescript-eslint/no-explicit-any -- SDK block types */
async function processImages(
  client: Lark.Client,
  docToken: string,
  markdown: string,
  insertedBlocks: any[],
  maxBytes: number,
): Promise<number> {
  /* eslint-enable @typescript-eslint/no-explicit-any */
  const imageUrls = extractImageUrls(markdown);
  if (imageUrls.length === 0) {
    return 0;
  }

  const imageBlocks = insertedBlocks.filter((b) => b.block_type === 27);

  let processed = 0;
  for (let i = 0; i < Math.min(imageUrls.length, imageBlocks.length); i++) {
    const url = imageUrls[i];
    const blockId = imageBlocks[i].block_id;

    try {
      const buffer = await downloadImage(url, maxBytes);
      const urlPath = new URL(url).pathname;
      const fileName = urlPath.split("/").pop() || `image_${i}.png`;
      const fileToken = await uploadImageToDocx(client, blockId, buffer, fileName);

      await client.docx.documentBlock.patch({
        path: { document_id: docToken, block_id: blockId },
        data: {
          replace_image: { token: fileToken },
        },
      });

      processed++;
    } catch (err) {
      console.error(`Failed to process image ${url}:`, err);
    }
  }

  return processed;
}

// ============ Actions ============

const STRUCTURED_BLOCK_TYPES = new Set([14, 18, 21, 23, 27, 30, 31, 32]);

async function readDoc(client: Lark.Client, docToken: string) {
  const [contentRes, infoRes, blocksRes] = await Promise.all([
    client.docx.document.rawContent({ path: { document_id: docToken } }),
    client.docx.document.get({ path: { document_id: docToken } }),
    client.docx.documentBlock.list({ path: { document_id: docToken } }),
  ]);

  if (contentRes.code !== 0) {
    throw new Error(contentRes.msg);
  }

  const blocks = blocksRes.data?.items ?? [];
  const blockCounts: Record<string, number> = {};
  const structuredTypes: string[] = [];

  for (const b of blocks) {
    const type = b.block_type ?? 0;
    const name = BLOCK_TYPE_NAMES[type] || `type_${type}`;
    blockCounts[name] = (blockCounts[name] || 0) + 1;

    if (STRUCTURED_BLOCK_TYPES.has(type) && !structuredTypes.includes(name)) {
      structuredTypes.push(name);
    }
  }

  let hint: string | undefined;
  if (structuredTypes.length > 0) {
    hint = `This document contains ${structuredTypes.join(", ")} which are NOT included in the plain text above. Use feishu_doc with action: "list_blocks" to get full content.`;
  }

  return {
    title: infoRes.data?.document?.title,
    content: contentRes.data?.content,
    revision_id: infoRes.data?.document?.revision_id,
    block_count: blocks.length,
    block_types: blockCounts,
    ...(hint && { hint }),
  };
}

function normalizeEditorOpenIds(openIds?: string[]): string[] {
  if (!Array.isArray(openIds)) return [];
  return Array.from(
    new Set(
      openIds
        .map((id) => String(id || "").trim())
        .filter((id) => id.length > 0 && id.startsWith("ou_")),
    ),
  );
}

async function grantDocEditors(
  client: Lark.Client,
  docToken: string,
  editorOpenIds: string[],
): Promise<{ requested: number; granted: string[]; failed: Array<{ open_id: string; reason: string }> }> {
  const granted: string[] = [];
  const failed: Array<{ open_id: string; reason: string }> = [];
  const tokenTypes = ["docx", "doc", "file"] as const;

  for (const openId of normalizeEditorOpenIds(editorOpenIds)) {
    let success = false;
    let lastErr = "";
    for (const tokenType of tokenTypes) {
      try {
        const res = await client.drive.permissionMember.create({
          path: { token: docToken },
          params: { type: tokenType as any, need_notification: false },
          data: {
            member_type: "openid",
            member_id: openId,
            perm: "edit",
          },
        });
        if (res.code === 0) {
          granted.push(openId);
          success = true;
          break;
        }
        lastErr = `type=${tokenType}, code=${res.code}, msg=${res.msg || "unknown"}`;
      } catch (err) {
        const e = err as any;
        const violation = Array.isArray(e?.field_violations)
          ? JSON.stringify(e.field_violations)
          : Array.isArray(e?.response?.data?.field_violations)
            ? JSON.stringify(e.response.data.field_violations)
            : "";
        const msg = e?.response?.data?.msg || e?.message || String(err);
        lastErr = `type=${tokenType}, msg=${msg}${violation ? `, field_violations=${violation}` : ""}`;
      }
    }
    if (!success) {
      failed.push({
        open_id: openId,
        reason: lastErr || "permission grant failed",
      });
    }
  }

  return { requested: editorOpenIds.length, granted, failed };
}

async function createDoc(client: Lark.Client, title: string, folderToken?: string) {
  const createData: Record<string, unknown> = { title };
  const normalizedFolderToken = String(folderToken ?? "").trim();
  if (normalizedFolderToken) {
    createData.folder_token = normalizedFolderToken;
  }
  const res = await client.docx.document.create({
    data: createData as any,
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }
  const doc = res.data?.document;
  return {
    document_id: doc?.document_id,
    title: doc?.title,
    url: `https://feishu.cn/docx/${doc?.document_id}`,
  };
}

async function writeDoc(
  client: Lark.Client,
  docToken: string,
  markdown: string,
  maxBytes: number,
  opts?: {
    titleHint?: string;
    autoIllustrate?: boolean;
    imagePrompt?: string;
    illustrationApiKey?: string;
  },
) {
  const enhanced = await enhanceMarkdownForDoc({
    markdown,
    titleHint: opts?.titleHint,
    autoIllustrate: opts?.autoIllustrate,
    imagePrompt: opts?.imagePrompt,
    illustrationApiKey: opts?.illustrationApiKey,
  });
  const deleted = await clearDocumentContent(client, docToken);

  const { blocks, firstLevelBlockIds } = await convertMarkdown(client, enhanced.markdown);
  if (blocks.length === 0) {
    return { success: true, blocks_deleted: deleted, blocks_added: 0, images_processed: 0 };
  }
  const sortedBlocks = sortBlocksByFirstLevel(blocks, firstLevelBlockIds);

  // Use Descendant API when content contains tables (Children API can't create tables)
  let inserted: any[];
  let skipped: string[];
  if (hasTableBlocks(blocks)) {
    const result = await insertBlocksInBatches(client, docToken, blocks, firstLevelBlockIds);
    inserted = result.children;
    skipped = result.skipped;
  } else {
    const result = await insertBlocks(client, docToken, sortedBlocks);
    inserted = result.children;
    skipped = result.skipped;
  }
  const imagesProcessed = await processImages(client, docToken, enhanced.markdown, inserted, maxBytes);

  const warnings = [
    ...(enhanced.warning ? [enhanced.warning] : []),
    ...(skipped.length > 0
      ? [`Skipped unsupported block types: ${skipped.join(", ")}.`]
      : []),
  ];

  return {
    success: true,
    blocks_deleted: deleted,
    blocks_added: inserted.length,
    images_processed: imagesProcessed,
    auto_illustrate: true,
    illustration_generated: enhanced.generated,
    ...(enhanced.generatedImageUrl ? { illustration_url: enhanced.generatedImageUrl } : {}),
    ...(warnings.length > 0 ? { warning: warnings.join(" | ") } : {}),
  };
}

async function appendDoc(
  client: Lark.Client,
  docToken: string,
  markdown: string,
  maxBytes: number,
  opts?: {
    titleHint?: string;
    autoIllustrate?: boolean;
    imagePrompt?: string;
    illustrationApiKey?: string;
  },
) {
  const enhanced = await enhanceMarkdownForDoc({
    markdown,
    titleHint: opts?.titleHint,
    autoIllustrate: opts?.autoIllustrate,
    imagePrompt: opts?.imagePrompt,
    illustrationApiKey: opts?.illustrationApiKey,
  });
  const { blocks, firstLevelBlockIds } = await convertMarkdown(client, enhanced.markdown);
  if (blocks.length === 0) {
    throw new Error("Content is empty");
  }
  const sortedBlocks = sortBlocksByFirstLevel(blocks, firstLevelBlockIds);

  // Use Descendant API when content contains tables (Children API can't create tables)
  let inserted: any[];
  let skipped: string[];
  if (hasTableBlocks(blocks)) {
    const result = await insertBlocksInBatches(client, docToken, blocks, firstLevelBlockIds);
    inserted = result.children;
    skipped = result.skipped;
  } else {
    const result = await insertBlocks(client, docToken, sortedBlocks);
    inserted = result.children;
    skipped = result.skipped;
  }
  const imagesProcessed = await processImages(client, docToken, enhanced.markdown, inserted, maxBytes);

  const warnings = [
    ...(enhanced.warning ? [enhanced.warning] : []),
    ...(skipped.length > 0
      ? [`Skipped unsupported block types: ${skipped.join(", ")}.`]
      : []),
  ];

  return {
    success: true,
    blocks_added: inserted.length,
    images_processed: imagesProcessed,
    auto_illustrate: true,
    illustration_generated: enhanced.generated,
    ...(enhanced.generatedImageUrl ? { illustration_url: enhanced.generatedImageUrl } : {}),
    ...(warnings.length > 0 ? { warning: warnings.join(" | ") } : {}),
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- SDK block type
    block_ids: inserted.map((b: any) => b.block_id),
  };
}

async function updateBlock(
  client: Lark.Client,
  docToken: string,
  blockId: string,
  content: string,
) {
  const blockInfo = await client.docx.documentBlock.get({
    path: { document_id: docToken, block_id: blockId },
  });
  if (blockInfo.code !== 0) {
    throw new Error(blockInfo.msg);
  }

  const res = await client.docx.documentBlock.patch({
    path: { document_id: docToken, block_id: blockId },
    data: {
      update_text_elements: {
        elements: [{ text_run: { content } }],
      },
    },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }

  return { success: true, block_id: blockId };
}

async function deleteBlock(client: Lark.Client, docToken: string, blockId: string) {
  const blockInfo = await client.docx.documentBlock.get({
    path: { document_id: docToken, block_id: blockId },
  });
  if (blockInfo.code !== 0) {
    throw new Error(blockInfo.msg);
  }

  const parentId = blockInfo.data?.block?.parent_id ?? docToken;

  const children = await client.docx.documentBlockChildren.get({
    path: { document_id: docToken, block_id: parentId },
  });
  if (children.code !== 0) {
    throw new Error(children.msg);
  }

  const items = children.data?.items ?? [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- SDK block type
  const index = items.findIndex((item: any) => item.block_id === blockId);
  if (index === -1) {
    throw new Error("Block not found");
  }

  const res = await client.docx.documentBlockChildren.batchDelete({
    path: { document_id: docToken, block_id: parentId },
    data: { start_index: index, end_index: index + 1 },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }

  return { success: true, deleted_block_id: blockId };
}

async function listBlocks(client: Lark.Client, docToken: string) {
  const res = await client.docx.documentBlock.list({
    path: { document_id: docToken },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }

  return {
    blocks: res.data?.items ?? [],
  };
}

async function getBlock(client: Lark.Client, docToken: string, blockId: string) {
  const res = await client.docx.documentBlock.get({
    path: { document_id: docToken, block_id: blockId },
  });
  if (res.code !== 0) {
    throw new Error(res.msg);
  }

  return {
    block: res.data?.block,
  };
}

async function listAppScopes(client: Lark.Client) {
  const res = await client.application.scope.list({});
  if (res.code !== 0) {
    throw new Error(res.msg);
  }

  const scopes = res.data?.scopes ?? [];
  const granted = scopes.filter((s) => s.grant_status === 1);
  const pending = scopes.filter((s) => s.grant_status !== 1);

  return {
    granted: granted.map((s) => ({ name: s.scope_name, type: s.scope_type })),
    pending: pending.map((s) => ({ name: s.scope_name, type: s.scope_type })),
    summary: `${granted.length} granted, ${pending.length} pending`,
  };
}

// ============ Tool Registration ============

export function registerFeishuDocTools(api: OpenClawPluginApi) {
  if (!api.config) {
    api.logger.debug?.("feishu_doc: No config available, skipping doc tools");
    return;
  }

  // Check if any account is configured
  const accounts = listEnabledFeishuAccounts(api.config);
  if (accounts.length === 0) {
    api.logger.debug?.("feishu_doc: No Feishu accounts configured, skipping doc tools");
    return;
  }

  // Use first account's config for tools configuration
  const firstAccount = accounts[0];
  const toolsCfg = resolveToolsConfig(firstAccount.config.tools);
  const mediaMaxBytes = (firstAccount.config?.mediaMaxMb ?? 30) * 1024 * 1024;
  const apiConfig = api.config as any;
  const qwenImageApiKey = String(
    apiConfig?.skills?.["qwen-image"]?.apiKey ??
      apiConfig?.models?.providers?.bailian?.apiKey ??
      process.env.DASHSCOPE_API_KEY ??
      "",
  ).trim();
  const defaultEditorOpenIds = normalizeEditorOpenIds(
    firstAccount.config?.docEditorOpenIds ??
      apiConfig?.channels?.feishu?.docEditorOpenIds ??
      apiConfig?.channels?.feishu?.allowFrom ??
      [],
  );

  // Helper to get client for the default account
  const getClient = () => createFeishuClient(firstAccount);
  const registered: string[] = [];

  // Main document tool with action-based dispatch
  if (toolsCfg.doc) {
    api.registerTool(
      {
        name: "feishu_doc",
        label: "Feishu Doc",
        description:
          "Feishu document operations. Actions: read, write, append, create, list_blocks, get_block, update_block, delete_block",
        parameters: FeishuDocSchema,
        async execute(_toolCallId: string, params: unknown) {
          const p = params as FeishuDocParams;
          try {
            const client = getClient();
            switch (p.action) {
              case "read":
                return json(await readDoc(client, p.doc_token));
              case "write":
                return json(
                  await writeDoc(client, p.doc_token, p.content, mediaMaxBytes, {
                    titleHint: p.doc_token,
                    autoIllustrate: (p as any).auto_illustrate,
                    imagePrompt: (p as any).image_prompt,
                    illustrationApiKey: qwenImageApiKey,
                  }),
                );
              case "append":
                return json(
                  await appendDoc(client, p.doc_token, p.content, mediaMaxBytes, {
                    titleHint: p.doc_token,
                    autoIllustrate: (p as any).auto_illustrate,
                    imagePrompt: (p as any).image_prompt,
                    illustrationApiKey: qwenImageApiKey,
                  }),
                );
              case "create": {
                const created = await createDoc(client, p.title, p.folder_token);
                const editorOpenIds = normalizeEditorOpenIds(
                  (p as any).editor_open_ids ?? defaultEditorOpenIds,
                );
                let editorGrant:
                  | { requested: number; granted: string[]; failed: Array<{ open_id: string; reason: string }> }
                  | undefined;
                if (created.document_id && editorOpenIds.length > 0) {
                  editorGrant = await grantDocEditors(client, created.document_id, editorOpenIds);
                }
                // If content is provided, immediately write it to the new document
                const content = (p as any).content as string | undefined;
                if (content && content.trim() && created.document_id) {
                  try {
                    const writeResult = await writeDoc(client, created.document_id, content, mediaMaxBytes, {
                      titleHint: p.title,
                      autoIllustrate: (p as any).auto_illustrate,
                      imagePrompt: (p as any).image_prompt,
                      illustrationApiKey: qwenImageApiKey,
                    });
                    const wr = writeResult as any;
                    return json({
                      ...created,
                      content_written: true,
                      blocks_added: writeResult.blocks_added,
                      images_processed: writeResult.images_processed,
                      ...(wr.illustration_generated !== undefined
                        ? { illustration_generated: wr.illustration_generated }
                        : {}),
                      ...(wr.illustration_url ? { illustration_url: wr.illustration_url } : {}),
                      ...(editorGrant ? { editor_permission: editorGrant } : {}),
                      ...(wr.warning ? { warning: wr.warning } : {}),
                    });
                  } catch (writeErr) {
                    return json({
                      ...created,
                      content_written: false,
                      ...(editorGrant ? { editor_permission: editorGrant } : {}),
                      warning: `文档已创建，但内容写入失败：${writeErr instanceof Error ? writeErr.message : String(writeErr)}`,
                    });
                  }
                }
                return json({
                  ...created,
                  ...(editorGrant ? { editor_permission: editorGrant } : {}),
                });
              }
              case "list_blocks":
                return json(await listBlocks(client, p.doc_token));
              case "get_block":
                return json(await getBlock(client, p.doc_token, p.block_id));
              case "update_block":
                return json(await updateBlock(client, p.doc_token, p.block_id, p.content));
              case "delete_block":
                return json(await deleteBlock(client, p.doc_token, p.block_id));
              default:
                // eslint-disable-next-line @typescript-eslint/no-explicit-any -- exhaustive check fallback
                return json({ error: `Unknown action: ${(p as any).action}` });
            }
          } catch (err) {
            return json({ error: err instanceof Error ? err.message : String(err) });
          }
        },
      },
      { name: "feishu_doc" },
    );
    registered.push("feishu_doc");
  }

  // Keep feishu_app_scopes as independent tool
  if (toolsCfg.scopes) {
    api.registerTool(
      {
        name: "feishu_app_scopes",
        label: "Feishu App Scopes",
        description:
          "List current app permissions (scopes). Use to debug permission issues or check available capabilities.",
        parameters: Type.Object({}),
        async execute() {
          try {
            const result = await listAppScopes(getClient());
            return json(result);
          } catch (err) {
            return json({ error: err instanceof Error ? err.message : String(err) });
          }
        },
      },
      { name: "feishu_app_scopes" },
    );
    registered.push("feishu_app_scopes");
  }

  if (registered.length > 0) {
    api.logger.info?.(`feishu_doc: Registered ${registered.join(", ")}`);
  }
}
