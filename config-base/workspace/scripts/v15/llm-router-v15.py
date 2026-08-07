#!/usr/bin/env python3
"""
V15 LLM 路由器 — 五层路由矩阵 + 降级链 + 路由日志
替代 cognitive-kernel-v6.py 中的 call_llm() + FALLBACK_CHAIN 路由逻辑

用法:
  # 作为模块导入
  router = LLMRouter()
  decision = router.route(text, classification)
  result = router.execute(decision, messages, system_prompt)

  # CLI 测试
  python3 scripts/v15/llm-router-v15.py --route "帮我写个Python脚本"
  python3 scripts/v15/llm-router-v15.py --call "你好"
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
OPENCLAW_HOME = Path(os.path.expanduser("~/.openclaw"))

# Codex OAuth 工具
try:
    _scripts_dir = str(Path(__file__).resolve().parent.parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from codex_auth import get_codex_config as _get_codex_config
except ImportError:
    _get_codex_config = None
STATE_DIR = WORKSPACE / "state"
ROUTING_LOG_DB = STATE_DIR / "v15-routing-log.db"
LLM_CACHE_DB = STATE_DIR / "v15-llm-cache.db"

LLM_CACHE_MAX = 500
LLM_CACHE_TTL = 3600 * 48  # 48h

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 路由决策数据结构
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class RoutingDecision:
    model: str = ""
    provider: str = ""
    fallback_chain: list = field(default_factory=list)
    rule_id: str = ""
    reason: str = ""
    speculative: bool = False
    use_cache: bool = True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 降级链定义
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FALLBACK_CHAIN = [
    ("deepseek", "deepseek-chat"),
    ("openai-codex", "gpt-5.4-mini"),
    ("deepseek", "deepseek-reasoner"),
    ("openai-codex", "gpt-5.4"),
    ("local-mini1", "Qwen3.5-9B-MLX-4bit"),
]

CODING_CHAIN = [
    ("deepseek", "deepseek-chat"),
    ("deepseek", "deepseek-reasoner"),
    ("openai-codex", "gpt-5.4"),
    ("openai-codex", "gpt-5.4-mini"),
    ("local-mini1", "Qwen3.5-9B-MLX-4bit"),
]

REASONING_CHAIN = [
    ("deepseek", "deepseek-reasoner"),
    ("openai-codex", "gpt-5.4"),
    ("deepseek", "deepseek-chat"),
    ("openai-codex", "gpt-5.4-mini"),
    ("local-mini1", "Qwen3.5-9B-MLX-4bit"),
]

VISION_CHAIN = [
    ("openai-codex", "gpt-5.4-mini"),
    ("openai-codex", "gpt-5.4"),
    ("deepseek", "deepseek-chat"),
]

ANALYSIS_CHAIN = [
    ("local-mini1", "Qwen3.5-9B-MLX-4bit"),
    ("deepseek", "deepseek-chat"),
    ("openai-codex", "gpt-5.4-mini"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Provider 信任级别
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROVIDER_TRUST = {
    "deepseek": {
        "trust_level": "full",
        "allowed_actions": "*",
        "max_tokens": 8000,
    },
    "openai-codex": {
        "trust_level": "full",
        "allowed_actions": "*",
        "max_tokens": 8000,
        "force_temperature": 0.1,
        "model_overrides": {
            "gpt-5.4-mini": {
                "trust_level": "full",
                "allowed_actions": "*",
                "max_tokens": 4000,
                "force_temperature": 0.1,
            },
            "gpt-5.4": {
                "trust_level": "full",
                "allowed_actions": "*",
                "max_tokens": 8000,
                "force_temperature": 0.1,
            },
        },
    },
    "local-mini1": {
        "trust_level": "full",
        "allowed_actions": "*",
        "max_tokens": 4000,
        "force_temperature": 0.1,
        "extra_body": {"enable_thinking": False},
    },
}

REASONER_MODELS = {"deepseek-reasoner"}

_NO_THINK_SYSTEM = "/no_think 你是一个精确的JSON输出助手。直接输出JSON，不要思维链，不要解释。"

_ANTI_HALLUCINATION_SYSTEM = (
    "你是一个精确、可靠的助手。请严格遵守以下规则：\n"
    "1. 只回答你确信的内容，不确定时明确说'我不确定'\n"
    "2. 不要编造不存在的API、函数、库名或技术细节\n"
    "3. 不要虚构数据、统计数字或引用来源\n"
    "4. 保持回复简洁，避免过度展开\n"
    "5. 如果问题超出你的能力范围，直接说明"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 超时策略
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_TIMEOUTS = {
    "deepseek-chat":         (3, 20),
    "deepseek-reasoner":     (3, 45),
    "gpt-5.4-mini":          (5, 30),
    "gpt-5.4":               (5, 60),
    "Qwen3.5-9B-MLX-4bit":  (1, 30),
    "Qwen2.5-7B-Instruct-4bit": (1, 10),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM Router 核心类
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LLMRouter:
    def __init__(self):
        self._openclaw_config = None
        self._log_db = None
        self._cache_db = None

    def _load_openclaw_config(self) -> dict:
        if self._openclaw_config is not None:
            return self._openclaw_config
        config_path = OPENCLAW_HOME / "openclaw.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._openclaw_config = json.load(f)
        else:
            self._openclaw_config = {}
        return self._openclaw_config

    # ── L1 闪电分类 ──

    def classify(self, text: str) -> dict:
        """L1 闪电分类 (mini1 Qwen2.5-7B, <1.6s, 准确率88%)
        返回: {intent, complexity, domain, requires_search, has_image}"""
        try:
            from pathlib import Path as _P
            sys_path = str(_P(__file__).parent)
            if sys_path not in sys.path:
                sys.path.insert(0, sys_path)
            # 优先使用 cluster-client 的 classify
            import importlib
            cc = importlib.import_module("cluster-client-v15".replace("-", "_"))
            return cc.classify(text)
        except Exception:
            pass
        # 回退: 简单规则分类
        result = {
            "intent": "unknown", "complexity": "medium",
            "domain": "general", "requires_search": False, "has_image": False,
        }
        if "__HAS_IMAGE__" in text:
            result["has_image"] = True
        if any(kw in text for kw in ["搜索", "查一下", "最新", "新闻"]):
            result["requires_search"] = True
        short = len(text.strip()) < 15
        if short and any(kw in text for kw in ["你好", "早", "晚安", "谢谢", "ok"]):
            result["intent"] = "greeting"
            result["complexity"] = "simple"
        return result

    # ── 路由决策 ──

    def route(self, text: str, classification: dict = None) -> RoutingDecision:
        """五层路由矩阵 R0-R8"""
        if classification is None:
            classification = {}

        intent = classification.get("intent", "unknown")
        complexity = classification.get("complexity", "medium")
        domain = classification.get("domain", "unknown")
        has_image = classification.get("has_image", False)
        requires_search = classification.get("requires_search", False)

        # R0: 有图片 → VISION_CHAIN
        if has_image:
            return RoutingDecision(
                model="gpt-5.4-mini", provider="openai-codex",
                fallback_chain=VISION_CHAIN, rule_id="R0",
                reason="has_image → vision chain"
            )

        # R2: simple + casual → 本地 9B
        if complexity == "simple" and intent in ("greeting", "casual_chat", "unknown"):
            return RoutingDecision(
                model="Qwen3.5-9B-MLX-4bit", provider="local-mini1",
                fallback_chain=ANALYSIS_CHAIN, rule_id="R2",
                reason="simple+casual → local 9B"
            )

        # R4: requires_search → Cloud + enable_search
        if requires_search:
            return RoutingDecision(
                model="deepseek-chat", provider="deepseek",
                fallback_chain=FALLBACK_CHAIN, rule_id="R4",
                reason="requires_search → cloud"
            )

        # R5: coding → CODING_CHAIN
        if intent == "coding" or domain == "code":
            return RoutingDecision(
                model="deepseek-chat", provider="deepseek",
                fallback_chain=CODING_CHAIN, rule_id="R5",
                reason="coding → coding chain"
            )

        # R6: complex + reasoning → REASONING_CHAIN
        if complexity == "complex" and intent in ("deep_analysis", "investment_decision", "quant_analysis"):
            return RoutingDecision(
                model="deepseek-reasoner", provider="deepseek",
                fallback_chain=REASONING_CHAIN, rule_id="R6",
                reason="complex+reasoning → reasoning chain"
            )

        # R7: medium → FALLBACK_CHAIN
        if complexity == "medium":
            return RoutingDecision(
                model="deepseek-chat", provider="deepseek",
                fallback_chain=FALLBACK_CHAIN, rule_id="R7",
                reason="medium → fallback chain"
            )

        # R8: default
        return RoutingDecision(
            model="deepseek-chat", provider="deepseek",
            fallback_chain=FALLBACK_CHAIN, rule_id="R8",
            reason="default → fallback chain"
        )

    # ── 执行路由决策 ──

    def execute(self, decision: RoutingDecision, prompt: str,
                user_input: str = "", action_type: str = "chat") -> str:
        """执行路由决策: 缓存 → 主模型 → 降级链"""
        # 缓存检查
        if decision.use_cache:
            ck = self._cache_key(prompt, user_input, action_type)
            cached = self._cache_get(ck)
            if cached is not None:
                self._record_routing(decision, "cache_hit", 0)
                return cached

        config = self._load_openclaw_config()
        providers = config.get("models", {}).get("providers", {})
        last_error = None

        chain = decision.fallback_chain or [(decision.provider, decision.model)]

        for provider_name, model_id in chain:
            provider_cfg = providers.get(provider_name, {})

            # 本地模型不需要 apiKey
            if provider_name.startswith("local-"):
                try:
                    result = self._call_local(model_id, prompt, action_type)
                    if result:
                        if decision.use_cache:
                            self._cache_put(self._cache_key(prompt, user_input, action_type), result)
                        self._record_routing(decision, "ok", 0, model_used=f"{provider_name}/{model_id}")
                        return result
                except Exception as e:
                    last_error = f"{provider_name}/{model_id}: {e}"
                    continue

            # openai-codex: 从 auth-profiles.json 读取 OAuth token
            if provider_name == "openai-codex" and (not provider_cfg or not provider_cfg.get("apiKey")):
                if _get_codex_config:
                    codex = _get_codex_config()
                    if codex["available"]:
                        provider_cfg = {"apiKey": codex["api_key"], "baseUrl": codex["base_url"]}
                    else:
                        last_error = f"{provider_name}/{model_id}: no codex credentials"
                        continue
                else:
                    last_error = f"{provider_name}/{model_id}: codex_auth not available"
                    continue
            elif not provider_cfg or not provider_cfg.get("apiKey"):
                continue

            # 模型准入检查
            if not self._is_action_allowed(provider_name, action_type, model_id):
                last_error = f"{provider_name}/{model_id}: blocked for {action_type}"
                continue

            try:
                t0 = time.monotonic()
                result = self._call_cloud(provider_cfg, model_id, prompt,
                                          provider_name=provider_name, action_type=action_type)
                latency_ms = int((time.monotonic() - t0) * 1000)

                if decision.use_cache:
                    self._cache_put(self._cache_key(prompt, user_input, action_type), result)
                self._record_routing(decision, "ok", latency_ms, model_used=f"{provider_name}/{model_id}")
                return result
            except Exception as e:
                last_error = f"{provider_name}/{model_id}: {e}"

        self._record_routing(decision, "all_failed", 0)
        raise Exception(f"All providers unavailable: {last_error}")

    # ── 云端调用 ──

    def _call_cloud(self, provider_cfg: dict, model_id: str, prompt: str,
                    provider_name: str = "deepseek", action_type: str = "chat") -> str:
        import requests
        url = f"{provider_cfg.get('baseUrl', '')}/chat/completions"
        timeout = _TIMEOUTS.get(model_id, (3, 15))
        trust = self._get_model_trust(provider_name, model_id)

        messages = []
        if provider_name.startswith("local"):
            messages.append({"role": "system", "content": _NO_THINK_SYSTEM})
        elif trust.get("trust_level") not in ("full", "coding", "reasoning"):
            messages.append({"role": "system", "content": _ANTI_HALLUCINATION_SYSTEM})
        messages.append({"role": "user", "content": prompt})

        body = {"model": model_id, "messages": messages, "max_tokens": trust.get("max_tokens", 4000)}
        if model_id not in REASONER_MODELS:
            body["temperature"] = trust.get("force_temperature", 0.1)

        extra = trust.get("extra_body", {})
        if extra:
            body.update(extra)

        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {provider_cfg['apiKey']}", "Content-Type": "application/json"},
            json=body, timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")

    # ── 本地调用 ──

    def _call_local(self, model_id: str, prompt: str, action_type: str = "chat") -> str:
        from urllib.request import urlopen, Request
        from urllib.error import URLError

        # 加载 v15 集群配置确定 URL
        config_path = WORKSPACE / "config" / "v15-cluster.json"
        url = "http://127.0.0.1:8000/v1/chat/completions"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cluster_cfg = json.load(f)
            url = cluster_cfg.get("cluster", {}).get("node1", {}).get("omlx_url", url)
            url = f"{url}/v1/chat/completions"

        messages = [
            {"role": "system", "content": _NO_THINK_SYSTEM if action_type in ("analysis", "intent_chain") else ""},
            {"role": "user", "content": prompt},
        ]
        messages = [m for m in messages if m["content"]]

        body = {"model": model_id, "messages": messages, "max_tokens": 4000, "temperature": 0.1}
        data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        choices = result.get("choices", [])
        return choices[0]["message"]["content"].strip() if choices else ""

    # ── 信任 & 准入 ──

    def _get_model_trust(self, provider_name: str, model_id: str = "") -> dict:
        trust = PROVIDER_TRUST.get(provider_name, {})
        if model_id and "model_overrides" in trust:
            override = trust["model_overrides"].get(model_id)
            if override:
                merged = {**trust, **override}
                merged.pop("model_overrides", None)
                return merged
        return trust

    def _is_action_allowed(self, provider_name: str, action_type: str, model_id: str = "") -> bool:
        trust = self._get_model_trust(provider_name, model_id)
        if trust.get("allowed_actions") == "*":
            return True
        blocked = trust.get("blocked_actions", [])
        if action_type in blocked:
            return False
        allowed = trust.get("allowed_actions", [])
        if allowed and action_type not in allowed:
            return False
        return True

    # ── LLM 缓存 ──

    def _get_cache_db(self) -> sqlite3.Connection:
        if self._cache_db is not None:
            return self._cache_db
        os.makedirs(STATE_DIR, exist_ok=True)
        self._cache_db = sqlite3.connect(str(LLM_CACHE_DB))
        self._cache_db.execute("PRAGMA journal_mode=WAL")
        self._cache_db.execute("PRAGMA synchronous=NORMAL")
        self._cache_db.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                key TEXT PRIMARY KEY, result TEXT, ts REAL
            )
        """)
        return self._cache_db

    def _cache_key(self, prompt: str, user_input: str = "", action_type: str = "") -> str:
        if user_input:
            key_src = f"{user_input[:100]}|{action_type}"
        else:
            key_src = prompt[:500]
        return hashlib.md5(key_src.encode()).hexdigest()

    def _cache_get(self, key: str):
        try:
            conn = self._get_cache_db()
            row = conn.execute("SELECT result, ts FROM llm_cache WHERE key = ?", (key,)).fetchone()
            if row and (time.time() - row[1]) < LLM_CACHE_TTL:
                return row[0]
            if row:
                conn.execute("DELETE FROM llm_cache WHERE key = ?", (key,))
                conn.commit()
        except Exception:
            pass
        return None

    def _cache_put(self, key: str, result: str):
        try:
            conn = self._get_cache_db()
            conn.execute("INSERT OR REPLACE INTO llm_cache VALUES (?,?,?)", (key, result, time.time()))
            count = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
            if count > LLM_CACHE_MAX:
                conn.execute("DELETE FROM llm_cache WHERE key IN (SELECT key FROM llm_cache ORDER BY ts ASC LIMIT ?)",
                             (count - LLM_CACHE_MAX,))
            conn.commit()
        except Exception:
            pass

    # ── 路由日志 ──

    def _get_log_db(self) -> sqlite3.Connection:
        if self._log_db is not None:
            return self._log_db
        os.makedirs(STATE_DIR, exist_ok=True)
        self._log_db = sqlite3.connect(str(ROUTING_LOG_DB))
        self._log_db.execute("PRAGMA journal_mode=WAL")
        self._log_db.execute("""
            CREATE TABLE IF NOT EXISTS routing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, rule_id TEXT, model TEXT, provider TEXT,
                model_used TEXT, status TEXT, latency_ms INTEGER, reason TEXT
            )
        """)
        return self._log_db

    def _record_routing(self, decision: RoutingDecision, status: str, latency_ms: int, model_used: str = ""):
        try:
            conn = self._get_log_db()
            conn.execute(
                "INSERT INTO routing_log (ts, rule_id, model, provider, model_used, status, latency_ms, reason) VALUES (?,?,?,?,?,?,?,?)",
                (time.strftime("%Y-%m-%dT%H:%M:%SZ"), decision.rule_id, decision.model,
                 decision.provider, model_used or f"{decision.provider}/{decision.model}",
                 status, latency_ms, decision.reason)
            )
            conn.commit()
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 兼容层: 保留 call_llm() 签名供旧代码调用
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_default_router = None

def _get_router() -> LLMRouter:
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router


def call_llm(prompt: str, config: dict = None, model: str = None, timeout: int = 15,
             user_input: str = "", action_type: str = "chat") -> str:
    """兼容层: 与 cognitive-kernel-v6.py 的 call_llm 签名一致"""
    router = _get_router()
    if config:
        router._openclaw_config = config
    classification = {"intent": action_type, "complexity": "medium", "domain": "unknown"}
    decision = router.route(user_input or prompt, classification)
    return router.execute(decision, prompt, user_input=user_input, action_type=action_type)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("V15 LLM Router")
        print("  --route TEXT    显示路由决策 (不实际调用)")
        print("  --call TEXT     路由 + 调用 LLM")
        print("  --stats         显示路由日志统计")
        sys.exit(0)

    cmd = sys.argv[1]
    router = LLMRouter()

    if cmd == "--route" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        # 先分类
        try:
            sys.path.insert(0, str(WORKSPACE / "scripts"))
            from v15 import cluster_client_v15 as cluster
            classification = cluster.classify(text)
        except Exception:
            classification = {"intent": "unknown", "complexity": "medium", "domain": "unknown"}
        decision = router.route(text, classification)
        print(f"分类: {json.dumps(classification, ensure_ascii=False)}")
        print(f"路由: {decision.rule_id} → {decision.provider}/{decision.model}")
        print(f"原因: {decision.reason}")
        print(f"降级链: {decision.fallback_chain}")

    elif cmd == "--call" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        t0 = time.time()
        try:
            result = call_llm("", user_input=text)
            dt = (time.time() - t0) * 1000
            print(result[:500])
            print(f"\n⏱️ {dt:.0f}ms")
        except Exception as e:
            print(f"❌ {e}")

    elif cmd == "--stats":
        try:
            conn = router._get_log_db()
            rows = conn.execute(
                "SELECT rule_id, model_used, status, COUNT(*), AVG(latency_ms) "
                "FROM routing_log GROUP BY rule_id, model_used, status ORDER BY COUNT(*) DESC LIMIT 20"
            ).fetchall()
            print(f"{'Rule':6s} {'Model':35s} {'Status':12s} {'Count':6s} {'Avg ms':8s}")
            print("-" * 70)
            for row in rows:
                print(f"{row[0]:6s} {row[1]:35s} {row[2]:12s} {row[3]:6d} {row[4]:8.0f}")
        except Exception as e:
            print(f"❌ {e}")
