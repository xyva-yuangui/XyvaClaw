#!/usr/bin/env node
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { FeishuShopperRuntime } from "../lib/feishu_runtime.mjs";

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token.startsWith("--")) {
      const key = token.slice(2);
      const maybe = argv[i + 1];
      if (!maybe || maybe.startsWith("--")) {
        out[key] = true;
      } else {
        out[key] = maybe;
        i += 1;
      }
    } else {
      out._.push(token);
    }
  }
  return out;
}

function parseCollectResult(raw) {
  try {
    const data = JSON.parse(String(raw || "{}"));
    const files = Array.isArray(data.results)
      ? data.results
          .flatMap((x) => {
            if (!x || !x.ok) return [];
            if (Array.isArray(x.files)) return x.files.map((f) => String(f));
            if (x.file) return [String(x.file)];
            return [];
          })
      : [];
    return { data, files };
  } catch {
    return { data: { parse_error: true, raw: String(raw || "") }, files: [] };
  }
}

function parseThreshold(raw, fallback) {
  if (raw === undefined || raw === null || raw === "") return fallback;
  const n = Number(raw);
  if (!Number.isFinite(n)) {
    throw new Error(`invalid --threshold: ${raw}`);
  }
  return n;
}

function asJson(value) {
  return JSON.stringify(value, null, 2);
}

function printUsage() {
  const lines = [
    "Usage:",
    "  node scripts/feishu_agent_runtime.mjs create --type flight --query '{\"from\":\"SHA\",\"to\":\"SZX\"}' --platforms feizhu,qunar,ctrip,meituan --operator momo",
    "  node scripts/feishu_agent_runtime.mjs advance --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs collect --task <task_id> --urls '[{\"source\":\"ctrip\",\"url\":\"https://...\"}]' --operator momo",
    "  node scripts/feishu_agent_runtime.mjs auto-compare --task <task_id> --urls '[{\"source\":\"ctrip\",\"url\":\"https://...\"}]' --item-selector '.item-card' --operator momo",
    "  node scripts/feishu_agent_runtime.mjs set-anchor --task <task_id> --keyword '特仑苏' --brand '蒙牛' --spec '250ml*24' --pack-count 24 --operator momo",
    "  node scripts/feishu_agent_runtime.mjs same-report --task <task_id> --threshold 0.78 --operator momo",
    "  node scripts/feishu_agent_runtime.mjs auto-compare-same --task <task_id> --urls '[{\"source\":\"jd\",\"url\":\"https://...\"}]' --spec '250ml*24' --threshold 0.78 --operator momo",
    "  node scripts/feishu_agent_runtime.mjs ingest --task <task_id> --files '/tmp/a.png,/tmp/b.png' --operator momo",
    "  node scripts/feishu_agent_runtime.mjs ocr-extract --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs extract --task <task_id> --offers '[{\"source\":\"ctrip\",\"final_price\":1280}]' --operator momo",
    "  node scripts/feishu_agent_runtime.mjs rank --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs draft --task <task_id> --offer <offer_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs risk-check --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs final-check --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs force-release --task <task_id> --operator momo",
    "  node scripts/feishu_agent_runtime.mjs cmd --text 'CONFIRM_SUBMIT <task_id>' --operator momo",
    "  node scripts/feishu_agent_runtime.mjs selected --task <task_id> --offer <offer_id>",
    "  node scripts/feishu_agent_runtime.mjs show --task <task_id>",
    "  node scripts/feishu_agent_runtime.mjs active",
  ];
  process.stdout.write(`${lines.join("\n")}\n`);
}

function parseQuery(raw) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`invalid --query JSON: ${raw}`);
  }
}

function parsePlatforms(raw) {
  if (!raw) return [];
  return String(raw)
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function parseFiles(raw) {
  if (!raw) return [];
  return String(raw)
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
}

function parseOffers(raw) {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error("offers must be array");
    return parsed;
  } catch {
    throw new Error("invalid --offers JSON array");
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const action = args._[0];
  if (!action || args.help) {
    printUsage();
    process.exit(0);
  }

  const root = fileURLToPath(new URL("..", import.meta.url));
  const runtime = new FeishuShopperRuntime({ root: path.resolve(root) });

  if (action === "create") {
    const task = runtime.createTask({
      type: String(args.type || "").toLowerCase(),
      query: parseQuery(args.query),
      platforms: parsePlatforms(args.platforms),
      createdBy: String(args.operator || "group_user"),
      note: String(args.note || ""),
    });
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "auto-compare") {
    const jobs = args.urls ? parseQuery(args.urls) : [];
    if (!Array.isArray(jobs)) throw new Error("--urls must be JSON array");
    const result = await runtime.autoCompare(args.task, jobs, String(args.operator || "system"), {
      wait: args.wait,
      fullPage: Boolean(args["full-page"]),
      scrollCount: args["scroll-count"],
      scrollStep: args["scroll-step"],
      scrollWait: args["scroll-wait"],
      itemSelector: args["item-selector"],
      offerId: args.offer,
    });
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "set-anchor") {
    const result = runtime.setSameProductAnchor(
      args.task,
      {
        keyword: args.keyword,
        brand: args.brand,
        title: args.title,
        spec: args.spec,
        pack_count: args["pack-count"],
      },
      String(args.operator || "system")
    );
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "same-report") {
    const result = runtime.sameProductReport(args.task, String(args.operator || "system"), {
      threshold: parseThreshold(args.threshold, undefined),
    });
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "auto-compare-same") {
    const jobs = args.urls ? parseQuery(args.urls) : [];
    if (!Array.isArray(jobs)) throw new Error("--urls must be JSON array");
    const anchor = {
      keyword: args.keyword,
      brand: args.brand,
      title: args.title,
      spec: args.spec,
      pack_count: args["pack-count"],
    };
    const result = await runtime.autoCompareSameProduct(args.task, jobs, String(args.operator || "system"), {
      wait: args.wait,
      fullPage: Boolean(args["full-page"]),
      scrollCount: args["scroll-count"],
      scrollStep: args["scroll-step"],
      scrollWait: args["scroll-wait"],
      itemSelector: args["item-selector"],
      threshold: parseThreshold(args.threshold, undefined),
      anchor,
    });
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "collect") {
    const collectScript = path.resolve(root, "scripts", "collect_screenshots.mjs");
    const collectArgs = [collectScript, "--task", String(args.task || "")];
    if (args.urls) collectArgs.push("--urls", String(args.urls));
    if (args["url-file"]) collectArgs.push("--url-file", String(args["url-file"]));
    if (args.wait) collectArgs.push("--wait", String(args.wait));
    if (args["full-page"]) collectArgs.push("--full-page");
    if (args["scroll-count"]) collectArgs.push("--scroll-count", String(args["scroll-count"]));
    if (args["scroll-step"]) collectArgs.push("--scroll-step", String(args["scroll-step"]));
    if (args["scroll-wait"]) collectArgs.push("--scroll-wait", String(args["scroll-wait"]));
    if (args["item-selector"]) collectArgs.push("--item-selector", String(args["item-selector"]));
    if (args["session-dir"]) collectArgs.push("--session-dir", String(args["session-dir"]));

    const child = spawnSync("node", collectArgs, {
      encoding: "utf8",
      timeout: 300000,
      maxBuffer: 4 * 1024 * 1024,
    });
    if (child.status !== 0) {
      throw new Error(`collect failed: ${(child.stderr || child.stdout || "unknown error").trim()}`);
    }

    const parsed = parseCollectResult(child.stdout);
    const task = runtime.ingestScreenshots(args.task, parsed.files, String(args.operator || "system"));
    process.stdout.write(
      `${asJson({
        task_id: task.task_id,
        state: task.state,
        ingested_count: parsed.files.length,
        collect: parsed.data,
      })}\n`
    );
    return;
  }

  if (action === "advance") {
    const task = runtime.advanceTask(args.task, String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "ingest") {
    const task = runtime.ingestScreenshots(args.task, parseFiles(args.files), String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "ocr-extract") {
    const task = runtime.ocrExtract(args.task, String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "extract") {
    const task = runtime.extractOffers(args.task, parseOffers(args.offers), String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "rank") {
    const task = runtime.rankOffers(args.task, String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "draft") {
    const task = runtime.buildCheckoutDraft(args.task, args.offer, String(args.operator || "system"));
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "final-check") {
    const result = runtime.finalCheck(args.task, String(args.operator || "system"));
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "force-release") {
    const result = runtime.forceReleaseActiveTask(args.task, String(args.operator || "system"), "cli_force_release");
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "risk-check") {
    const result = runtime.riskCheck(args.task, String(args.operator || "system"));
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "cmd") {
    const result = runtime.handleFeishuText(String(args.text || ""), String(args.operator || "group_user"));
    process.stdout.write(`${asJson(result)}\n`);
    return;
  }

  if (action === "show") {
    const task = runtime.getTask(args.task);
    process.stdout.write(`${asJson(task)}\n`);
    return;
  }

  if (action === "selected") {
    const selected = runtime.getSelectedOfferSnapshot(args.task, args.offer);
    process.stdout.write(`${asJson(selected)}\n`);
    return;
  }

  if (action === "active") {
    const active = runtime.state.activeTaskId ? runtime.getTask(runtime.state.activeTaskId) : null;
    process.stdout.write(`${asJson({ active_task_id: runtime.state.activeTaskId, task: active })}\n`);
    return;
  }

  throw new Error(`unsupported action: ${action}`);
}

main().catch((err) => {
  process.stderr.write(`${String(err.stack || err)}\n`);
  process.exit(1);
});
