#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token.startsWith("--")) {
      const key = token.slice(2);
      const maybe = argv[i + 1];
      if (!maybe || maybe.startsWith("--")) out[key] = true;
      else {
        out[key] = maybe;
        i += 1;
      }
    } else {
      out._.push(token);
    }
  }
  return out;
}

function parseExtractedText(stdout) {
  const raw = String(stdout || "").trim();
  if (!raw) return "";
  const lines = raw.split(/\r?\n/);
  const kept = [];
  for (const line of lines) {
    const s = line.trim();
    if (!s) continue;
    if (s.startsWith("{") && s.includes("screenshot_files")) continue;
    kept.push(line);
  }
  return kept.join("\n").trim();
}

function nowTag() {
  return new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
}

function parseJsonArg(raw, fallback) {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw);
  } catch {
    throw new Error(`invalid JSON argument: ${raw}`);
  }
}

function usage() {
  process.stdout.write(
    [
      "Usage:",
      "  node scripts/collect_screenshots.mjs --task <task_id> --urls '[{\"source\":\"ctrip\",\"url\":\"https://...\"}]'",
      "  node scripts/collect_screenshots.mjs --task <task_id> --url-file /tmp/urls.json",
      "",
      "Options:",
      "  --task <task_id>         required",
      "  --urls <json-array>      array of {source,url}",
      "  --url-file <path>        file containing the same JSON array",
      "  --wait <ms>              page wait time, default 2500",
      "  --full-page              full page screenshot",
      "  --scroll-count <n>       auto scroll times, default 2",
      "  --scroll-step <px>       scroll pixels each time, default 1200",
      "  --scroll-wait <ms>       wait after scroll, default 1200",
      "  --item-selector <css>    screenshot the first matching item card only",
      "  --session-dir <path>     persistent browser session root",
      "",
      "Notes:",
      "  - Uses browser-pilot script to open each URL and save PNG",
      "  - Writes image files into runtime/evidence/<task_id>/",
    ].join("\n") + "\n"
  );
}

function readUrlJobs(args) {
  if (args["url-file"]) {
    const p = path.resolve(String(args["url-file"]));
    const raw = fs.readFileSync(p, "utf8");
    return parseJsonArg(raw, []);
  }
  return parseJsonArg(args.urls, []);
}

function resolveBrowserPilotScript() {
  const candidates = [
    path.resolve(process.env.HOME || "", ".openclaw/workspace/skills/browser-pilot/scripts/browse.mjs"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  throw new Error("browser-pilot script not found");
}

function safeName(x) {
  return String(x || "unknown").replace(/[^a-zA-Z0-9_-]/g, "_");
}

function parseScreenshotFiles(stdout, fallbackFile) {
  const raw = String(stdout || "").trim();
  if (!raw) return [fallbackFile];
  const lines = raw.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (!line.startsWith("{")) continue;
    try {
      const parsed = JSON.parse(line);
      const files = Array.isArray(parsed?.screenshot_files)
        ? parsed.screenshot_files.map((x) => String(x)).filter(Boolean)
        : [];
      return files.length > 0 ? files : [fallbackFile];
    } catch {
      // ignore
    }
  }
  return [fallbackFile];
}

function main() {
  const args = parseArgs(process.argv);
  if (!args.task || args.help) {
    usage();
    process.exit(args.help ? 0 : 2);
  }

  const jobs = readUrlJobs(args);
  if (!Array.isArray(jobs) || jobs.length === 0) {
    throw new Error("no URL jobs provided");
  }

  const waitMs = Number(args.wait || 2500);
  const fullPage = Boolean(args["full-page"]);
  const scrollCount = Math.max(0, Number(args["scroll-count"] || 2));
  const scrollStep = Math.max(200, Number(args["scroll-step"] || 1200));
  const scrollWait = Math.max(100, Number(args["scroll-wait"] || 1200));
  const itemSelector = String(args["item-selector"] || "").trim();

  const __filename = fileURLToPath(import.meta.url);
  const __dirname = path.dirname(__filename);
  const root = path.resolve(__dirname, "..");
  const evidenceDir = path.join(root, "runtime", "evidence", String(args.task));
  const sessionRoot = path.resolve(String(args["session-dir"] || path.join(root, "runtime", "sessions")));
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.mkdirSync(sessionRoot, { recursive: true });

  const browserScript = resolveBrowserPilotScript();
  const results = [];

  for (let i = 0; i < jobs.length; i += 1) {
    const job = jobs[i] || {};
    const source = safeName(job.source || `platform_${i + 1}`);
    const url = String(job.url || "").trim();
    if (!url) {
      results.push({ ok: false, source, error: "missing url" });
      continue;
    }

    const png = path.join(evidenceDir, `${nowTag()}_${i + 1}_${source}.png`);
    const userDataDir = path.join(sessionRoot, source);
    const cmdArgs = [
      browserScript,
      "--url",
      url,
      "--screenshot",
      png,
      "--extract-text",
      "--selector",
      String(job.selector || "body"),
      "--wait",
      String(waitMs),
      "--user-data-dir",
      userDataDir,
      "--scroll-count",
      String(scrollCount),
      "--scroll-step",
      String(scrollStep),
      "--scroll-wait",
      String(scrollWait),
    ];
    if (fullPage) cmdArgs.push("--full-page");
    if (itemSelector) cmdArgs.push("--screenshot-selector", itemSelector);

    const child = spawnSync("node", cmdArgs, {
      encoding: "utf8",
      timeout: 180000,
      maxBuffer: 2 * 1024 * 1024,
    });

    if (child.status === 0) {
      const files = parseScreenshotFiles(child.stdout, png).filter((x) => fs.existsSync(x));
      const text = parseExtractedText(child.stdout);
      for (const f of files) {
        if (text) {
          fs.writeFileSync(`${f}.txt`, text, "utf8");
        }
      }
      if (files.length > 0) {
        results.push({ ok: true, source, url, file: files[0], files, user_data_dir: userDataDir });
      } else {
        results.push({
          ok: false,
          source,
          url,
          file: png,
          files: [],
          error: "screenshot files missing",
        });
      }
    } else {
      results.push({
        ok: false,
        source,
        url,
        file: png,
        files: [],
        error: (child.stderr || child.stdout || "browse failed").trim(),
      });
    }
  }

  process.stdout.write(`${JSON.stringify({ task_id: args.task, evidence_dir: evidenceDir, results }, null, 2)}\n`);
}

try {
  main();
} catch (err) {
  process.stderr.write(`${String(err?.message || err)}\n`);
  process.exit(1);
}
