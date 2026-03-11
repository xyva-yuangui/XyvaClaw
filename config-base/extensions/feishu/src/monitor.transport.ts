import * as http from "http";
import * as Lark from "@larksuiteoapi/node-sdk";
import {
  applyBasicWebhookRequestGuards,
  type RuntimeEnv,
  installRequestBodyLimitGuard,
} from "openclaw/plugin-sdk/feishu";
import { createFeishuWSClient, createFeishuClient } from "./client.js";
import { fetchBotIdentityForMonitor } from "./monitor.startup.js";
import {
  botNames,
  botOpenIds,
  FEISHU_WEBHOOK_BODY_TIMEOUT_MS,
  FEISHU_WEBHOOK_MAX_BODY_BYTES,
  feishuWebhookRateLimiter,
  httpServers,
  recordWebhookStatus,
  wsClients,
} from "./monitor.state.js";
import type { ResolvedFeishuAccount } from "./types.js";

/** Best-effort shutdown notice to DM allowlist users. Fire-and-forget. */
async function sendShutdownNotice(account: ResolvedFeishuAccount, log: (...args: any[]) => void): Promise<void> {
  const allowFrom = account.config?.allowFrom;
  if (!Array.isArray(allowFrom) || allowFrom.length === 0) return;
  try {
    const client = createFeishuClient(account);
    const notice = "⚙️ OpenClaw 正在重启维护，约 10 秒后恢复，期间消息可能延迟。";
    // Only notify first allowFrom user (owner) to avoid spam
    const ownerId = allowFrom[0];
    if (!ownerId || typeof ownerId !== "string") return;
    await client.im.message.create({
      params: { receive_id_type: "open_id" },
      data: {
        receive_id: ownerId,
        msg_type: "text",
        content: JSON.stringify({ text: notice }),
      },
    });
    log(`feishu[${account.accountId ?? "default"}]: sent shutdown notice to owner ${ownerId}`);
  } catch (err) {
    log(`feishu[${account.accountId ?? "default"}]: shutdown notice failed (best-effort): ${String(err)}`);
  }
}

export type MonitorTransportParams = {
  account: ResolvedFeishuAccount;
  accountId: string;
  runtime?: RuntimeEnv;
  abortSignal?: AbortSignal;
  eventDispatcher: Lark.EventDispatcher;
};

export async function monitorWebSocket({
  account,
  accountId,
  runtime,
  abortSignal,
  eventDispatcher,
}: MonitorTransportParams): Promise<void> {
  const log = runtime?.log ?? console.log;
  log(`feishu[${accountId}]: starting WebSocket connection...`);

  const wsClient = createFeishuWSClient(account);
  wsClients.set(accountId, wsClient);

  return new Promise((resolve, reject) => {
    let closeCount = 0;
    let errorCount = 0;
    let lastConnectedAt = Date.now();
    const healthProbeTimer = setInterval(() => {
      void fetchBotIdentityForMonitor(account, { runtime, abortSignal })
        .then(({ botOpenId }) => {
          log(
            `feishu[${accountId}]: ws health ok (bot=${botOpenId ?? "unknown"}, closeCount=${closeCount}, errorCount=${errorCount}, upMs=${Date.now() - lastConnectedAt})`,
          );
        })
        .catch((err) => {
          log(`feishu[${accountId}]: ws health probe failed: ${String(err)}`);
        });
    }, 60_000);
    healthProbeTimer.unref();

    const cleanup = () => {
      clearInterval(healthProbeTimer);
      wsClients.delete(accountId);
      botOpenIds.delete(accountId);
      botNames.delete(accountId);
    };

    const handleAbort = () => {
      log(`feishu[${accountId}]: abort signal received, stopping`);
      // Best-effort shutdown notice (fire-and-forget, don't block shutdown)
      void sendShutdownNotice(account, log);
      cleanup();
      resolve();
    };

    if (abortSignal?.aborted) {
      cleanup();
      resolve();
      return;
    }

    abortSignal?.addEventListener("abort", handleAbort, { once: true });

    try {
      // Hook into WSClient lifecycle events for observability.
      // Defensive: only patch if the SDK still exposes these internal methods.
      if (typeof (wsClient as any).onClose === "function" || (wsClient as any).onClose === undefined) {
        const origOnClose = (wsClient as any).onClose;
        (wsClient as any).onClose = (...args: any[]) => {
          closeCount += 1;
          log(`feishu[${accountId}]: ⚠️ WebSocket closed (count=${closeCount}, upMs=${Date.now() - lastConnectedAt})`);
          origOnClose?.apply(wsClient, args);
        };
      }
      if (typeof (wsClient as any).onError === "function" || (wsClient as any).onError === undefined) {
        const origOnError = (wsClient as any).onError;
        (wsClient as any).onError = (...args: any[]) => {
          errorCount += 1;
          log(`feishu[${accountId}]: ❌ WebSocket error (count=${errorCount}): ${String(args[0] ?? "unknown")}`);
          origOnError?.apply(wsClient, args);
        };
      }

      wsClient.start({ eventDispatcher });
      lastConnectedAt = Date.now();
      log(`feishu[${accountId}]: WebSocket client started`);
    } catch (err) {
      cleanup();
      abortSignal?.removeEventListener("abort", handleAbort);
      reject(err);
    }
  });
}

export async function monitorWebhook({
  account,
  accountId,
  runtime,
  abortSignal,
  eventDispatcher,
}: MonitorTransportParams): Promise<void> {
  const log = runtime?.log ?? console.log;
  const error = runtime?.error ?? console.error;

  const port = account.config.webhookPort ?? 3000;
  const path = account.config.webhookPath ?? "/feishu/events";
  const host = account.config.webhookHost ?? "127.0.0.1";

  log(`feishu[${accountId}]: starting Webhook server on ${host}:${port}, path ${path}...`);

  const server = http.createServer();
  const webhookHandler = Lark.adaptDefault(path, eventDispatcher, { autoChallenge: true });

  server.on("request", (req, res) => {
    res.on("finish", () => {
      recordWebhookStatus(runtime, accountId, path, res.statusCode);
    });

    const rateLimitKey = `${accountId}:${path}:${req.socket.remoteAddress ?? "unknown"}`;
    if (
      !applyBasicWebhookRequestGuards({
        req,
        res,
        rateLimiter: feishuWebhookRateLimiter,
        rateLimitKey,
        nowMs: Date.now(),
        requireJsonContentType: true,
      })
    ) {
      return;
    }

    const guard = installRequestBodyLimitGuard(req, res, {
      maxBytes: FEISHU_WEBHOOK_MAX_BODY_BYTES,
      timeoutMs: FEISHU_WEBHOOK_BODY_TIMEOUT_MS,
      responseFormat: "text",
    });
    if (guard.isTripped()) {
      return;
    }

    void Promise.resolve(webhookHandler(req, res))
      .catch((err) => {
        if (!guard.isTripped()) {
          error(`feishu[${accountId}]: webhook handler error: ${String(err)}`);
        }
      })
      .finally(() => {
        guard.dispose();
      });
  });

  httpServers.set(accountId, server);

  return new Promise((resolve, reject) => {
    const cleanup = () => {
      server.close();
      httpServers.delete(accountId);
      botOpenIds.delete(accountId);
      botNames.delete(accountId);
    };

    const handleAbort = () => {
      log(`feishu[${accountId}]: abort signal received, stopping Webhook server`);
      cleanup();
      resolve();
    };

    if (abortSignal?.aborted) {
      cleanup();
      resolve();
      return;
    }

    abortSignal?.addEventListener("abort", handleAbort, { once: true });

    server.listen(port, host, () => {
      log(`feishu[${accountId}]: Webhook server listening on ${host}:${port}`);
    });

    server.on("error", (err) => {
      error(`feishu[${accountId}]: Webhook server error: ${err}`);
      abortSignal?.removeEventListener("abort", handleAbort);
      reject(err);
    });
  });
}
