import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const DEFAULT_ROOT = path.resolve(path.dirname(new URL("..", import.meta.url).pathname));
const RUNTIME_ROOT = (process.env.COMMERCE_SHOPPER_ROOT || DEFAULT_ROOT).trim();
const RUNTIME_MODULE = path.join(RUNTIME_ROOT, "lib", "feishu_runtime.mjs");
const VERSION_PATH = path.join(RUNTIME_ROOT, "VERSION");
let cachedRuntime = null;
const STATUS_CACHE_TTL_MS = Math.max(200, Number(process.env.COMMERCE_STATUS_CACHE_TTL_MS || 1200));
const runtimeStatusCache = new Map();

const HELP_TEXT = [
  "SHOP HELP",
  "SHOP DOCTOR",
  "SHOP CREATE --type <flight|hotel|product> --query '<json>' --platforms <p1,p2>",
  "SHOP ACTIVE",
  "SHOP STATUS (alias of ACTIVE)",
  "SHOP SHOW [task_id]",
  "SHOP REPORT [task_id]",
  "SHOP SELECTED [task_id] [--offer <offer_id>]",
  "SHOP SET_ANCHOR [task_id] --keyword <k> [--brand <b>] [--spec <spec>] [--pack-count <n>]",
  "SHOP SAME_REPORT [task_id] [--threshold <0-1>]",
  "SHOP COLLECT [task_id] --urls '<json_array>' [--item-selector '.item-card']",
  "SHOP AUTO_COMPARE [task_id] --urls '<json_array>' [--item-selector '.item-card']",
  "SHOP AUTO_COMPARE_SAME [task_id] --urls '<json_array>' [--spec <spec>] [--threshold <0-1>]",
  "SHOP INGEST [task_id] --files '/tmp/a.png,/tmp/b.png' (or attach images)",
  "SHOP OCR_EXTRACT [task_id]",
  "SHOP EXTRACT --offers '<json_array>'",
  "SHOP RANK [task_id]",
  "SHOP DRAFT [task_id] --offer <offer_id>",
  "SHOP RISK_CHECK [task_id]",
  "SHOP FINAL_CHECK [task_id]",
  "SHOP FORCE_RELEASE [task_id]",
  "SHOP ADVANCE [task_id]",
  "CONFIRM_SUBMIT [task_id] / CONFIRM_PAY [task_id] / ABORT [task_id]",
].join("\n");

function assertRuntimePaths() {
  if (!fs.existsSync(RUNTIME_ROOT)) {
    throw new Error(`runtime root not found: ${RUNTIME_ROOT}. Set COMMERCE_SHOPPER_ROOT explicitly.`);
  }
  if (!fs.existsSync(RUNTIME_MODULE)) {
    throw new Error(`runtime module missing: ${RUNTIME_MODULE}.`);
  }
}

function toUpperToken(v) {
  return String(v || "").trim().toUpperCase();
}

function parseNum(raw, fallback) {
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function parseOptionalNum(raw, flagName) {
  if (raw === undefined || raw === "") return undefined;
  const n = Number(raw);
  if (!Number.isFinite(n)) {
    throw new Error(`invalid ${flagName}: ${raw}`);
  }
  return n;
}

function formatTaskReport(task) {
  const lines = [
    "📌 commerce-travel-shopper 任务报告",
    `- task_id: ${task?.task_id ?? "-"}`,
    `- type: ${task?.task_type ?? "-"}`,
    `- state: ${task?.state ?? "-"}`,
    `- offers: ${Array.isArray(task?.offers) ? task.offers.length : 0}`,
    `- evidence: ${Array.isArray(task?.evidence) ? task.evidence.length : 0}`,
    `- recommended_offer: ${task?.ranking?.recommended_offer_id ?? "-"}`,
    `- checkout_offer: ${task?.checkout_draft?.offer_id ?? "-"}`,
    `- confirm_submit: ${task?.execution?.confirm_submit ? "yes" : "no"}`,
    `- confirm_pay: ${task?.execution?.confirm_pay ? "yes" : "no"}`,
    `- updated_at: ${task?.updated_at ?? "-"}`,
  ];
  return lines.join("\n");
}

function splitTokens(input) {
  const out = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m;
  while ((m = re.exec(input))) {
    out.push(m[1] ?? m[2] ?? m[3] ?? "");
  }
  return out;
}

function parseArgs(tokens) {
  const positional = [];
  const options = {};
  for (let i = 0; i < tokens.length; i += 1) {
    const t = tokens[i];
    if (!t.startsWith("--")) {
      positional.push(t);
      continue;
    }
    const key = t.slice(2);
    const next = tokens[i + 1];
    if (!next || next.startsWith("--")) {
      options[key] = "true";
      continue;
    }
    options[key] = next;
    i += 1;
  }
  return { positional, options };
}

function parseJsonObject(raw) {
  if (!raw) return {};
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("--query must be a JSON object");
  }
  return parsed;
}

function parseJsonArray(raw, hint = "--offers") {
  if (!raw) return [];
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed)) throw new Error(`${hint} must be a JSON array`);
  return parsed;
}

function parseCsv(raw) {
  if (!raw) return [];
  return raw
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function stringifyResult(value) {
  const body = JSON.stringify(value, null, 2);
  const clipped = body.length > 3000 ? `${body.slice(0, 3000)}\n...truncated...` : body;
  return `✅ commerce-travel-shopper\n\n\`\`\`json\n${clipped}\n\`\`\``;
}

function readStatusCache(key) {
  const cached = runtimeStatusCache.get(key);
  if (!cached) return null;
  if (cached.expireAt <= Date.now()) {
    runtimeStatusCache.delete(key);
    return null;
  }
  return cached.value;
}

function writeStatusCache(key, value) {
  runtimeStatusCache.set(key, {
    expireAt: Date.now() + STATUS_CACHE_TTL_MS,
    value,
  });
}

function readVersion() {
  try {
    return fs.readFileSync(VERSION_PATH, "utf8").trim() || "unknown";
  } catch {
    return "unknown";
  }
}

function buildDoctor(runtime) {
  const runtimeDoctor =
    runtime && typeof runtime.getDoctorSnapshot === "function"
      ? runtime.getDoctorSnapshot()
      : {
          active_task_id: runtime?.state?.activeTaskId || null,
        };
  return {
    runtime_root: RUNTIME_ROOT,
    runtime_module: RUNTIME_MODULE,
    runtime_root_env: process.env.COMMERCE_SHOPPER_ROOT ? "set" : "default",
    version: readVersion(),
    ...runtimeDoctor,
    checked_at: new Date().toISOString(),
  };
}

async function createRuntime() {
  if (cachedRuntime) return cachedRuntime;
  assertRuntimePaths();
  const mod = await import(pathToFileURL(RUNTIME_MODULE).href);
  if (!mod.FeishuShopperRuntime) {
    throw new Error(`FeishuShopperRuntime export not found in ${RUNTIME_MODULE}`);
  }
  cachedRuntime = new mod.FeishuShopperRuntime({ root: RUNTIME_ROOT });
  return cachedRuntime;
}

export function isCommerceShopperCommand(content) {
  const raw = String(content || "").trim();
  if (!raw) return false;
  const upper = toUpperToken(raw.split(/\s+/)[0]);
  if (upper === "SHOP") return true;
  return ["CONFIRM_SUBMIT", "CONFIRM_PAY", "ABORT", "FORCE_RELEASE", "确认提交", "确认支付", "取消任务", "终止任务", "强制解锁"].includes(upper);
}

export async function executeCommerceShopperCommand(params) {
  const { content, operator, mediaPaths = [] } = params;
  const raw = String(content || "").trim();
  const rawTokens = splitTokens(raw);
  let first = toUpperToken(raw.split(/\s+/)[0]);
  if (first === "确认提交") first = "CONFIRM_SUBMIT";
  if (first === "确认支付") first = "CONFIRM_PAY";
  if (first === "取消任务" || first === "终止任务") first = "ABORT";
  if (first === "强制解锁") first = "FORCE_RELEASE";
  const normalizedRaw = rawTokens.length > 0 ? [first, ...rawTokens.slice(1)].join(" ") : raw;

  if (first === "CONFIRM_SUBMIT" || first === "CONFIRM_PAY" || first === "ABORT" || first === "FORCE_RELEASE") {
    const runtime = await createRuntime();
    const commandText = first === "FORCE_RELEASE" ? `SHOP FORCE_RELEASE ${rawTokens[1] || ""}`.trim() : normalizedRaw;
    const result = first === "FORCE_RELEASE"
      ? runtime.forceReleaseActiveTask(rawTokens[1] || undefined, operator || "group_user", "feishu_direct_force_release")
      : runtime.handleFeishuText(commandText, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  const allTokens = splitTokens(normalizedRaw);
  if (toUpperToken(allTokens[0]) !== "SHOP") {
    throw new Error("unsupported command");
  }
  const action = toUpperToken(allTokens[1] || "HELP");
  const { positional, options } = parseArgs(allTokens.slice(2));

  if (action === "HELP") {
    return { text: `🧭 commerce-travel-shopper commands\n\n${HELP_TEXT}` };
  }

  const runtime = await createRuntime();

  if (action === "DOCTOR") {
    const cacheKey = `DOCTOR:${String(runtime?.state?.activeTaskId || "none")}`;
    const cached = readStatusCache(cacheKey);
    if (cached) {
      return { text: stringifyResult(cached) };
    }
    const doctor = buildDoctor(runtime);
    writeStatusCache(cacheKey, doctor);
    return { text: stringifyResult(doctor) };
  }

  if (action === "CREATE") {
    const type = String(options.type || positional[0] || "").toLowerCase();
    if (!type) throw new Error("missing --type");
    const query = parseJsonObject(options.query);
    const platforms = parseCsv(options.platforms);
    const result = runtime.createTask({
      type,
      query,
      platforms,
      createdBy: operator || "group_user",
      note: String(options.note || ""),
    });
    return { text: stringifyResult(result) };
  }

  if (action === "ACTIVE" || action === "STATUS") {
    const activeTaskId = runtime.state.activeTaskId;
    const cacheKey = `ACTIVE:${String(activeTaskId || "none")}`;
    const cached = readStatusCache(cacheKey);
    if (cached) {
      return { text: stringifyResult(cached) };
    }
    const result = activeTaskId ? runtime.getTask(activeTaskId) : { active_task_id: null };
    writeStatusCache(cacheKey, result);
    return { text: stringifyResult(result) };
  }

  if (action === "SHOW") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.getTask(taskId || undefined);
    return { text: stringifyResult(result) };
  }

  if (action === "REPORT") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.getTask(taskId || undefined);
    return { text: `${formatTaskReport(result)}\n\n${stringifyResult(result)}` };
  }

  if (action === "SELECTED") {
    const taskId = String(options.task || positional[0] || "");
    const offerId = String(options.offer || positional[1] || "");
    const result = runtime.getSelectedOfferSnapshot(taskId || undefined, offerId || undefined);
    const imagePaths = Array.isArray(result?.selected_evidence)
      ? result.selected_evidence.map((ev) => (typeof ev?.file === "string" ? ev.file : "")).filter(Boolean)
      : [];
    return {
      text: `🎯 selected offer snapshot (only chosen item evidence)\n\n${stringifyResult(result)}`,
      imagePaths,
    };
  }

  if (action === "SET_ANCHOR") {
    const taskId = String(options.task || positional[0] || "");
    const packCount = parseOptionalNum(options["pack-count"], "--pack-count");
    const anchor = {
      keyword: String(options.keyword || ""),
      brand: String(options.brand || ""),
      title: String(options.title || ""),
      spec: String(options.spec || ""),
      pack_count: packCount,
    };
    const result = runtime.setSameProductAnchor(taskId || undefined, anchor, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "SAME_REPORT") {
    const taskId = String(options.task || positional[0] || "");
    const threshold = parseOptionalNum(options.threshold || positional[1], "--threshold");
    const result = runtime.sameProductReport(taskId || undefined, operator || "group_user", { threshold });
    return { text: `📊 same-product report\n\n${stringifyResult(result)}` };
  }

  if (action === "COLLECT") {
    const taskId = String(options.task || positional[0] || "");
    const jobs = parseJsonArray(options.urls, "--urls");
    if (!jobs.length) throw new Error("COLLECT requires --urls JSON array");
    const result = await runtime.collectScreenshots(taskId || undefined, jobs, operator || "group_user", {
      wait: parseNum(options.wait, 3000),
      fullPage: options["full-page"] === "true",
      scrollCount: parseNum(options["scroll-count"], 3),
      scrollStep: parseNum(options["scroll-step"], 1200),
      scrollWait: parseNum(options["scroll-wait"], 1000),
      itemSelector: String(options["item-selector"] || ""),
    });
    return { text: stringifyResult(result) };
  }

  if (action === "AUTO_COMPARE") {
    const taskId = String(options.task || positional[0] || "");
    const jobs = options.urls ? parseJsonArray(options.urls, "--urls") : [];
    const result = await runtime.autoCompare(taskId || undefined, jobs, operator || "group_user", {
      wait: parseNum(options.wait, 3000),
      fullPage: options["full-page"] === "true",
      scrollCount: parseNum(options["scroll-count"], 3),
      scrollStep: parseNum(options["scroll-step"], 1200),
      scrollWait: parseNum(options["scroll-wait"], 1000),
      itemSelector: String(options["item-selector"] || ""),
      offerId: String(options.offer || ""),
    });
    const selectedEvidence = result?.selected?.selected_evidence;
    const imagePaths = Array.isArray(selectedEvidence)
      ? selectedEvidence.map((ev) => (typeof ev?.file === "string" ? ev.file : "")).filter(Boolean)
      : [];
    return {
      text: `🤖 autonomous compare finished\n\n${stringifyResult(result)}`,
      imagePaths,
    };
  }

  if (action === "AUTO_COMPARE_SAME") {
    const taskId = String(options.task || positional[0] || "");
    const jobs = options.urls ? parseJsonArray(options.urls, "--urls") : [];
    const threshold = parseOptionalNum(options.threshold, "--threshold");
    const packCount = parseOptionalNum(options["pack-count"], "--pack-count");
    const anchor = {
      keyword: String(options.keyword || ""),
      brand: String(options.brand || ""),
      title: String(options.title || ""),
      spec: String(options.spec || ""),
      pack_count: packCount,
    };
    const result = await runtime.autoCompareSameProduct(taskId || undefined, jobs, operator || "group_user", {
      wait: parseNum(options.wait, 3000),
      fullPage: options["full-page"] === "true",
      scrollCount: parseNum(options["scroll-count"], 3),
      scrollStep: parseNum(options["scroll-step"], 1200),
      scrollWait: parseNum(options["scroll-wait"], 1000),
      itemSelector: String(options["item-selector"] || ""),
      threshold,
      anchor,
    });
    return { text: `🤖 same-product auto compare finished\n\n${stringifyResult(result)}` };
  }

  if (action === "INGEST") {
    const taskId = String(options.task || positional[0] || "");
    const filesFromText = parseCsv(options.files);
    const files = [...new Set([...filesFromText, ...mediaPaths])];
    if (files.length === 0) throw new Error("INGEST requires --files or attached images");
    const result = runtime.ingestScreenshots(taskId || undefined, files, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "OCR_EXTRACT") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.ocrExtract(taskId || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "EXTRACT") {
    const taskId = String(options.task || positional[0] || "");
    const offers = parseJsonArray(options.offers, "--offers");
    const result = runtime.extractOffers(taskId || undefined, offers, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "RANK") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.rankOffers(taskId || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "DRAFT") {
    const taskId = String(options.task || positional[0] || "");
    const offer = String(options.offer || positional[1] || "");
    const result = runtime.buildCheckoutDraft(taskId || undefined, offer || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "FINAL_CHECK") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.finalCheck(taskId || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "RISK_CHECK") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.riskCheck(taskId || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "ADVANCE") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.advanceTask(taskId || undefined, operator || "group_user");
    return { text: stringifyResult(result) };
  }

  if (action === "ABORT") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.abort(taskId || undefined, operator || "group_user", "feishu_shop_command");
    return { text: stringifyResult(result) };
  }

  if (action === "FORCE_RELEASE") {
    const taskId = String(options.task || positional[0] || "");
    const result = runtime.forceReleaseActiveTask(taskId || undefined, operator || "group_user", "feishu_shop_force_release");
    return { text: stringifyResult(result) };
  }

  throw new Error(`unsupported SHOP action: ${action}`);
}
