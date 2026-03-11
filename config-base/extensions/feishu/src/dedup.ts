import os from "node:os";
import path from "node:path";
import {
  createDedupeCache,
  createPersistentDedupe,
  readJsonFileWithFallback,
} from "openclaw/plugin-sdk/feishu";

// Persistent TTL: 12 hours — balances dedup safety with memory efficiency.
const DEDUP_TTL_MS = 12 * 60 * 60 * 1000;
const MEMORY_MAX_SIZE = 2_000;
const FILE_MAX_ENTRIES = 10_000;
type PersistentDedupeData = Record<string, number>;

const memoryDedupe = createDedupeCache({ ttlMs: DEDUP_TTL_MS, maxSize: MEMORY_MAX_SIZE });

function resolveStateDirFromEnv(env: NodeJS.ProcessEnv = process.env): string {
  const stateOverride = env.OPENCLAW_STATE_DIR?.trim() || env.CLAWDBOT_STATE_DIR?.trim();
  if (stateOverride) {
    return stateOverride;
  }
  if (env.VITEST || env.NODE_ENV === "test") {
    return path.join(os.tmpdir(), ["openclaw-vitest", String(process.pid)].join("-"));
  }
  return path.join(os.homedir(), ".openclaw");
}

function resolveNamespaceFilePath(namespace: string): string {
  const safe = namespace.replace(/[^a-zA-Z0-9_-]/g, "_");
  return path.join(resolveStateDirFromEnv(), "feishu", "dedup", `${safe}.json`);
}

const persistentDedupe = createPersistentDedupe({
  ttlMs: DEDUP_TTL_MS,
  memoryMaxSize: MEMORY_MAX_SIZE,
  fileMaxEntries: FILE_MAX_ENTRIES,
  resolveFilePath: resolveNamespaceFilePath,
});

const pendingPersistByNamespace = new Map<string, Set<string>>();
const persistFlushTimers = new Map<string, NodeJS.Timeout>();
const PERSIST_FLUSH_DELAY_MS = 1_000;

function schedulePersistentFlush(namespace: string, log?: (...args: unknown[]) => void): void {
  if (persistFlushTimers.has(namespace)) {
    return;
  }
  const timer = setTimeout(() => {
    persistFlushTimers.delete(namespace);
    const pending = pendingPersistByNamespace.get(namespace);
    if (!pending || pending.size === 0) {
      return;
    }
    pendingPersistByNamespace.delete(namespace);
    for (const messageId of pending) {
      void persistentDedupe.checkAndRecord(messageId, {
        namespace,
        onDiskError: (error: unknown) => {
          log?.(`feishu-dedup: async disk persist failed: ${String(error)}`);
        },
      });
    }
  }, PERSIST_FLUSH_DELAY_MS);
  timer.unref();
  persistFlushTimers.set(namespace, timer);
}

/**
 * Synchronous dedup — memory only.
 * Kept for backward compatibility; prefer {@link tryRecordMessagePersistent}.
 */
export function tryRecordMessage(messageId: string): boolean {
  return !memoryDedupe.check(messageId);
}

export function hasRecordedMessage(messageId: string): boolean {
  const trimmed = messageId.trim();
  if (!trimmed) {
    return false;
  }
  return memoryDedupe.peek(trimmed);
}

export async function tryRecordMessagePersistent(
  messageId: string,
  namespace = "global",
  log?: (...args: unknown[]) => void,
): Promise<boolean> {
  const trimmed = messageId.trim();
  if (!trimmed) {
    return false;
  }
  // Fast path: in-memory dedupe for hot route.
  if (!tryRecordMessage(trimmed)) {
    return false;
  }
  // Async persistence: keep durable dedupe without blocking message handling.
  const pending = pendingPersistByNamespace.get(namespace) ?? new Set<string>();
  pending.add(trimmed);
  pendingPersistByNamespace.set(namespace, pending);
  schedulePersistentFlush(namespace, log);
  return true;
}

export async function hasRecordedMessagePersistent(
  messageId: string,
  namespace = "global",
  log?: (...args: unknown[]) => void,
): Promise<boolean> {
  const trimmed = messageId.trim();
  if (!trimmed) {
    return false;
  }
  const now = Date.now();
  const filePath = resolveNamespaceFilePath(namespace);
  try {
    const { value } = await readJsonFileWithFallback<PersistentDedupeData>(filePath, {});
    const seenAt = value[trimmed];
    if (typeof seenAt !== "number" || !Number.isFinite(seenAt)) {
      return false;
    }
    return DEDUP_TTL_MS <= 0 || now - seenAt < DEDUP_TTL_MS;
  } catch (error) {
    log?.(`feishu-dedup: persistent peek failed: ${String(error)}`);
    return false;
  }
}

export async function warmupDedupFromDisk(
  namespace: string,
  log?: (...args: unknown[]) => void,
): Promise<number> {
  return persistentDedupe.warmup(namespace, (error: unknown) => {
    log?.(`feishu-dedup: warmup disk error: ${String(error)}`);
  });
}
