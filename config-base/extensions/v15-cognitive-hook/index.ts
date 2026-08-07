/**
 * v15-cognitive-hook — 把 V15 认知预分析接入每轮消息
 *
 * 机制: 注册 `before_prompt_build` 钩子 → 调用
 *   workspace/scripts/v15/cognitive-core-v15.py --analyze "<用户消息>"
 * 该模式只跑 L0 规则引擎 + 记忆检索 + 技能预选，**不调用任何 LLM**，
 * 结果以 prependContext 注入当轮 prompt；生成仍由 Gateway 自己的模型完成。
 *
 * 设计约束:
 *  - register() 必须同步（加载器不 await，异步会导致注册丢失）
 *  - 一律开放失败(fail-open)：超时/报错/非法输出都返回 {}，绝不阻塞对话
 *  - 硬超时 + kill 子进程，避免拖慢用户等待
 *  - 连续失败达阈值后自动熄火，防止每轮都白等
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

type AnalyzeResult = {
  ok?: boolean;
  context?: string;
  intent?: string;
  rule_id?: string | null;
  memory_hits?: number;
  latency_ms?: number;
};

type HookConfig = {
  enabled: boolean;
  timeoutMs: number;
  pythonBin: string;
  scriptPath: string;
  minChars: number;
  maxContextChars: number;
  maxConsecutiveFailures: number;
};

const DEFAULTS: HookConfig = {
  enabled: true,
  timeoutMs: 1200,
  pythonBin: "python3",
  scriptPath: join(homedir(), ".openclaw/workspace/scripts/v15/cognitive-core-v15.py"),
  minChars: 2,
  maxContextChars: 1200,
  maxConsecutiveFailures: 5,
};

function resolveConfig(raw: unknown): HookConfig {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const num = (v: unknown, d: number) =>
    typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.floor(v) : d;
  const str = (v: unknown, d: string) => (typeof v === "string" && v.trim() ? v.trim() : d);
  return {
    enabled: r.enabled === undefined ? DEFAULTS.enabled : r.enabled !== false,
    timeoutMs: num(r.timeoutMs, DEFAULTS.timeoutMs),
    pythonBin: str(r.pythonBin, DEFAULTS.pythonBin),
    scriptPath: str(r.scriptPath, DEFAULTS.scriptPath),
    minChars: num(r.minChars, DEFAULTS.minChars),
    maxContextChars: num(r.maxContextChars, DEFAULTS.maxContextChars),
    maxConsecutiveFailures: num(r.maxConsecutiveFailures, DEFAULTS.maxConsecutiveFailures),
  };
}

/** 从 hook 事件里尽力取出用户本轮输入（不同版本字段名可能不同） */
function extractUserText(event: unknown): string {
  const e = (event && typeof event === "object" ? event : {}) as Record<string, unknown>;
  for (const key of ["prompt", "userInput", "text", "message", "content"]) {
    const v = e[key];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  const msgs = e.messages;
  if (Array.isArray(msgs)) {
    for (let i = msgs.length - 1; i >= 0; i--) {
      const m = (msgs[i] || {}) as Record<string, unknown>;
      if (m.role !== "user") continue;
      const c = m.content;
      if (typeof c === "string" && c.trim()) return c.trim();
      if (Array.isArray(c)) {
        const text = c
          .map((p) => {
            const part = (p || {}) as Record<string, unknown>;
            return typeof part.text === "string" ? part.text : "";
          })
          .join(" ")
          .trim();
        if (text) return text;
      }
    }
  }
  return "";
}

/** 心跳/系统轮询类消息不做分析，避免无谓开销 */
function isSkippable(text: string): boolean {
  if (!text) return true;
  const t = text.trim();
  if (t.startsWith("HEARTBEAT")) return true;
  if (/^Read HEARTBEAT\.md/i.test(t)) return true;
  return false;
}

function runAnalyze(cfg: HookConfig, text: string): Promise<AnalyzeResult | null> {
  return new Promise((resolve) => {
    let settled = false;
    const done = (v: AnalyzeResult | null) => {
      if (!settled) {
        settled = true;
        resolve(v);
      }
    };

    let child: ReturnType<typeof spawn>;
    try {
      child = spawn(cfg.pythonBin, [cfg.scriptPath, "--analyze", text], {
        stdio: ["ignore", "pipe", "ignore"],
      });
    } catch {
      done(null);
      return;
    }

    const timer = setTimeout(() => {
      try {
        child.kill("SIGKILL");
      } catch {
        /* ignore */
      }
      done(null);
    }, cfg.timeoutMs);

    let stdout = "";
    child.stdout?.on("data", (chunk: unknown) => {
      // 分析输出只有一行 JSON；设上限防异常输出打爆内存
      if (stdout.length < 64_000) stdout += String(chunk);
    });
    child.on("error", () => {
      clearTimeout(timer);
      done(null);
    });
    child.on("close", () => {
      clearTimeout(timer);
      const start = stdout.indexOf("{");
      if (start < 0) {
        done(null);
        return;
      }
      try {
        done(JSON.parse(stdout.slice(start)) as AnalyzeResult);
      } catch {
        done(null);
      }
    });
  });
}

const plugin = {
  id: "v15-cognitive-hook",
  name: "V15 Cognitive Hook",
  description:
    "Injects V15 rule-engine intent, memory hits and skill hints into every turn via before_prompt_build",

  configSchema: {
    parse(value: unknown) {
      return resolveConfig(value);
    },
  },

  register(api: any) {
    // api.pluginConfig = 本插件自己的配置（plugins.entries.<id>.config）；
    // api.config 是全局配置，不能当插件配置用。与 lossless-claw 写法一致。
    const rawCfg =
      api?.pluginConfig && typeof api.pluginConfig === "object" && !Array.isArray(api.pluginConfig)
        ? api.pluginConfig
        : {};
    const cfg: HookConfig = resolveConfig(rawCfg);

    if (!cfg.enabled) {
      api?.logger?.info?.("[v15-hook] disabled by config");
      return;
    }
    if (!existsSync(cfg.scriptPath)) {
      api?.logger?.warn?.(
        `[v15-hook] cognitive-core not found at ${cfg.scriptPath}; hook not registered`,
      );
      return;
    }

    let consecutiveFailures = 0;
    let mutedReason = "";

    const handler = async (event: unknown, _ctx: unknown) => {
      if (mutedReason) return {};

      const text = extractUserText(event);
      if (isSkippable(text) || text.length < cfg.minChars) return {};

      const result = await runAnalyze(cfg, text);

      if (!result || result.ok === false) {
        consecutiveFailures += 1;
        if (consecutiveFailures >= cfg.maxConsecutiveFailures) {
          mutedReason = `${consecutiveFailures} consecutive failures`;
          api?.logger?.warn?.(`[v15-hook] muted after ${mutedReason}; restart gateway to retry`);
        }
        return {};
      }

      consecutiveFailures = 0;
      const ctxText = (result.context || "").slice(0, cfg.maxContextChars);
      if (!ctxText) return {};

      api?.logger?.debug?.(
        `[v15-hook] intent=${result.intent} rule=${result.rule_id} mem=${result.memory_hits} ${result.latency_ms}ms`,
      );
      return { prependContext: ctxText };
    };

    // 必须用 api.on —— 它走 registerTypedHook（Plugin Hooks，返回值会被采纳）。
    // api.registerHook 是另一套 Internal Hooks（字符串事件、**无返回值**），
    // 用它注册会静默生效但 prependContext 被完全忽略，所以不能做降级选项。
    if (typeof api?.on !== "function") {
      api?.logger?.warn?.(
        "[v15-hook] api.on 不可用（需支持 typed plugin hooks 的 OpenClaw 版本），未注册",
      );
      return;
    }
    api.on("before_prompt_build", handler, {
      name: "v15-cognitive-analyze",
      description: "V15 rule/memory/skill pre-analysis injected into each turn",
    });

    api?.logger?.info?.(
      `[v15-hook] registered (timeout=${cfg.timeoutMs}ms, script=${cfg.scriptPath})`,
    );
  },
};

export default plugin;
