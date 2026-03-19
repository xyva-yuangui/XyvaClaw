import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const DEFAULT_ROOT = path.join(
  process.env.HOME || "",
  ".openclaw",
  "workspace",
  "skills",
  "commerce-travel-shopper",
);
const RUNTIME_ROOT = (process.env.COMMERCE_SHOPPER_ROOT || DEFAULT_ROOT).trim();
const CORE_MODULE = path.join(RUNTIME_ROOT, "lib", "feishu_bridge_core.mjs");

function toUpperToken(v: string): string {
  return String(v || "").trim().toUpperCase();
}

export type CommerceShopperCommandReply = {
  text: string;
  imagePaths?: string[];
};

type BridgeCore = {
  isCommerceShopperCommand: (content: string) => boolean;
  executeCommerceShopperCommand: (params: {
    content: string;
    operator: string;
    mediaPaths?: string[];
  }) => Promise<CommerceShopperCommandReply>;
};

let cachedCore: BridgeCore | null = null;
let bridgeUnavailable = false;

async function loadBridgeCore(): Promise<BridgeCore> {
  if (cachedCore) return cachedCore;
  if (bridgeUnavailable) throw new Error(`bridge core previously failed to load: ${CORE_MODULE}`);
  try {
    const mod = (await import(pathToFileURL(CORE_MODULE).href)) as Partial<BridgeCore>;
    if (typeof mod.isCommerceShopperCommand !== "function" || typeof mod.executeCommerceShopperCommand !== "function") {
      throw new Error(`invalid bridge core module: ${CORE_MODULE}`);
    }
    cachedCore = mod as BridgeCore;
    return cachedCore;
  } catch (err) {
    bridgeUnavailable = true;
    throw err;
  }
}

export function isCommerceShopperCommand(content: string): boolean {
  // If module previously failed to load, skip command detection entirely.
  if (bridgeUnavailable) return false;
  const raw = String(content || "").trim();
  if (!raw) return false;
  const first = toUpperToken(raw.split(/\s+/)[0]);
  return ["SHOP", "CONFIRM_SUBMIT", "CONFIRM_PAY", "ABORT", "FORCE_RELEASE", "确认提交", "确认支付", "取消任务", "终止任务", "强制解锁"].includes(first);
}

export async function executeCommerceShopperCommand(params: {
  content: string;
  operator: string;
  mediaPaths?: string[];
}): Promise<CommerceShopperCommandReply> {
  const core = await loadBridgeCore();
  return core.executeCommerceShopperCommand(params);
}
