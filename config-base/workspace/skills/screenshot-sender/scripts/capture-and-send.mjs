#!/usr/bin/env node

/**
 * capture-and-send.mjs
 * Capture a macOS screenshot and optionally send it to a Feishu chat.
 *
 * Usage:
 *   node capture-and-send.mjs [--mode full|window|region] [--chat <chat_id>] [--file <path>] [--caption <text>] [--output <path>] [--no-send]
 */

import { execSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { parseArgs } from "node:util";

const DEFAULT_CHAT = "__GROUP_ID__";

const { values: args } = parseArgs({
  options: {
    mode:    { type: "string",  default: "full" },
    chat:    { type: "string",  default: DEFAULT_CHAT },
    file:    { type: "string",  default: "" },
    caption: { type: "string",  default: "" },
    output:  { type: "string",  default: "" },
    "no-send": { type: "boolean", default: false },
  },
  strict: false,
});

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
}

function captureScreenshot(mode, outputPath) {
  const flags = ["-x", "-o"]; // silent, no shadow
  if (mode === "window") flags.push("-w");
  else if (mode === "region") flags.push("-s");
  // "full" uses no extra flag

  const cmd = `/usr/sbin/screencapture ${flags.join(" ")} "${outputPath}"`;
  console.error(`[screenshot] Capturing (${mode}): ${cmd}`);
  try {
    execSync(cmd, { stdio: "inherit", timeout: 30_000 });
  } catch (err) {
    console.error(`[screenshot] Capture failed: ${err.message}`);
    process.exit(1);
  }

  if (!existsSync(outputPath)) {
    console.error(`[screenshot] File not created (user may have cancelled): ${outputPath}`);
    process.exit(1);
  }
  console.error(`[screenshot] Saved: ${outputPath}`);
  return outputPath;
}

function getOpenClawGateway() {
  // Read gateway config from openclaw.json
  const configPaths = [
    resolve(process.env.HOME, ".openclaw/openclaw.json"),
  ];
  for (const p of configPaths) {
    if (existsSync(p)) {
      try {
        const cfg = JSON.parse(readFileSync(p, "utf-8"));
        const port = cfg?.gateway?.port || 18789;
        const token = cfg?.gateway?.auth?.token || "";
        return { port, token };
      } catch { /* ignore */ }
    }
  }
  return { port: 18789, token: "" };
}

async function sendToFeishu(imagePath, chatId, caption) {
  const { port, token } = getOpenClawGateway();
  const baseUrl = `http://127.0.0.1:${port}`;

  // Step 1: Upload image via gateway /api/v1/media/upload (if available)
  // Fallback: use exec tool to call feishu image upload
  // For now, we use the openclaw CLI approach: send the file path as a message
  // and let the agent handle the upload via feishu plugin tools

  // Output the file path for the agent to pick up
  const result = {
    success: true,
    imagePath: resolve(imagePath),
    chatId,
    caption: caption || "",
    timestamp: new Date().toISOString(),
    instructions: "Use feishu_doc or media upload API to send this image to the chat. The image is at the path above.",
  };

  console.log(JSON.stringify(result, null, 2));
  return result;
}

async function main() {
  let imagePath = args.file;

  // If no existing file provided, capture a new screenshot
  if (!imagePath) {
    const outputPath = args.output || `/tmp/screenshot_${timestamp()}.png`;
    imagePath = captureScreenshot(args.mode, outputPath);
  } else {
    imagePath = resolve(imagePath);
    if (!existsSync(imagePath)) {
      console.error(`[screenshot] File not found: ${imagePath}`);
      process.exit(1);
    }
  }

  if (args["no-send"]) {
    console.log(JSON.stringify({ success: true, imagePath, sent: false }));
    return;
  }

  await sendToFeishu(imagePath, args.chat, args.caption);
}

main().catch((err) => {
  console.error(`[screenshot] Error: ${err.message}`);
  process.exit(1);
});
