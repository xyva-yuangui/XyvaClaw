#!/usr/bin/env python3
"""
V15 集群通信客户端 — 统一封装本地 oMLX 和云端 LLM 的所有 API 调用
替代 v12-cluster-client.py, 清除所有 ollama 命名

用法:
  # 作为模块导入
  from v15.cluster_client_v15 import embed, classify, local_chat, perceive, call_cloud

  # CLI 测试
  python3 scripts/v15/cluster-client-v15.py --test
  python3 scripts/v15/cluster-client-v15.py --embed "测试文本"
  python3 scripts/v15/cluster-client-v15.py --classify "帮我分析一下茅台的走势"
"""
from __future__ import annotations

import json
import hashlib
import os
import sqlite3
import struct
import time
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
CONFIG_PATH = WORKSPACE / "config" / "v15-cluster.json"
STATE_DIR = WORKSPACE / "state"
EMBED_CACHE_DB = STATE_DIR / "v15-embedding-cache.db"

_config_cache = None


def load_config() -> dict:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    else:
        # 回退到 v12 配置
        fallback = WORKSPACE / "config" / "v12-cluster.json"
        if fallback.exists():
            with open(fallback, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
        else:
            _config_cache = {}
    return _config_cache


def _omlx_request(url: str, payload: dict, timeout: int = 60) -> dict:
    """发送请求到 oMLX 推理服务 (OpenAI 兼容格式)"""
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        return {"error": f"URLError: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layer 0: 向量嵌入 (bge-m3, mini2 常驻)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_embed_db_conn = None

def _get_embed_db() -> sqlite3.Connection:
    global _embed_db_conn
    if _embed_db_conn is not None:
        return _embed_db_conn
    os.makedirs(STATE_DIR, exist_ok=True)
    _embed_db_conn = sqlite3.connect(str(EMBED_CACHE_DB))
    _embed_db_conn.execute("PRAGMA journal_mode=WAL")
    _embed_db_conn.execute("""
        CREATE TABLE IF NOT EXISTS embedding_cache (
            text_hash TEXT PRIMARY KEY,
            embedding_bin BLOB,
            model TEXT,
            created_at TEXT
        )
    """)
    return _embed_db_conn


def _pack_vec(vec: list[float]) -> bytes:
    return struct.pack(f'{len(vec)}f', *vec)


def _unpack_vec(data: bytes) -> list[float]:
    n = len(data) // 4
    return list(struct.unpack(f'{n}f', data))


def embed(text: str, use_cache: bool = True) -> list[float]:
    """获取文本向量嵌入 (bge-m3, mini2)"""
    cfg = load_config()
    emb_cfg = cfg.get("models", {}).get("embedding", {})
    url = emb_cfg.get("url", "http://127.0.0.1:11434/v1/embeddings")
    model = emb_cfg.get("model", "bge-m3-mlx-fp16")

    text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

    if use_cache:
        try:
            db = _get_embed_db()
            row = db.execute("SELECT embedding_bin FROM embedding_cache WHERE text_hash = ?", (text_hash,)).fetchone()
            if row and row[0]:
                return _unpack_vec(row[0])
        except Exception:
            pass

    result = _omlx_request(url, {"model": model, "input": text}, timeout=15)
    embedding = result.get("data", [{}])[0].get("embedding", []) if "data" in result else []

    if not embedding or "error" in result:
        return []

    if use_cache and embedding:
        try:
            db = _get_embed_db()
            db.execute(
                "INSERT OR REPLACE INTO embedding_cache (text_hash, embedding_bin, model, created_at) VALUES (?, ?, ?, ?)",
                (text_hash, _pack_vec(embedding), model, time.strftime("%Y-%m-%dT%H:%M:%SZ"))
            )
            db.commit()
        except Exception:
            pass

    return embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def embed_batch(texts: list[str]) -> list[list[float]]:
    return [embed(t) for t in texts]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layer 1: 闪电分类 (Qwen2.5-7B, mini1 本地)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLASSIFY_SYSTEM = (
    "/no_think 你是意图分类器。输出严格JSON，不要解释。\n"
    "格式: {\"intent\":\"<类别>\",\"complexity\":\"simple|medium|complex\","
    "\"domain\":\"<领域>\",\"requires_search\":false,\"has_image\":false}"
)

CLASSIFY_INTENTS = (
    "greeting, casual_chat, quant_analysis, xhs_content, video_creation, "
    "coding, question, task_management, content_creation, image_generation, "
    "translation, system_management, investment_decision, deep_analysis, "
    "web_search, file_operation, send_message, unknown"
)

CLASSIFY_DOMAINS = (
    "chat, finance, tech, content, media, code, knowledge, life, system, unknown"
)


def classify(text: str, timeout: int = 8) -> dict:
    """L1 闪电分类 — mini1 Qwen2.5-7B (<1.6s)
    返回: {intent, complexity, domain, requires_search, has_image}
    """
    cfg = load_config()
    c_cfg = cfg.get("models", {}).get("classifier", {})
    url = c_cfg.get("url", "http://127.0.0.1:8000/v1/chat/completions")
    model = c_cfg.get("model", "Qwen2.5-7B-Instruct-4bit")
    max_tokens = c_cfg.get("max_output_tokens", 100)

    user_prompt = (
        f"可选意图: {CLASSIFY_INTENTS}\n"
        f"可选领域: {CLASSIFY_DOMAINS}\n"
        f"用户输入: {text[:300]}\n"
        f"输出JSON:"
    )

    result = _omlx_request(url, {
        "model": model,
        "messages": [
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.05,
    }, timeout=timeout)

    choices = result.get("choices", [])
    raw = choices[0]["message"]["content"].strip() if choices else ""

    # 解析 JSON
    try:
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        parsed = json.loads(raw.strip())
        # 标准化
        return {
            "intent": parsed.get("intent", "unknown"),
            "complexity": parsed.get("complexity", "medium"),
            "domain": parsed.get("domain", "unknown"),
            "requires_search": parsed.get("requires_search", False),
            "has_image": parsed.get("has_image", False),
        }
    except (json.JSONDecodeError, KeyError, IndexError):
        return {
            "intent": "unknown",
            "complexity": "medium",
            "domain": "unknown",
            "requires_search": False,
            "has_image": False,
            "_raw": raw[:200],
            "_error": "classify_parse_failed",
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layer 2: 本地生成 (Qwen3.5-9B, mini1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def local_chat(messages: list[dict], max_tokens: int = 500, temperature: float = 0.7,
               system_prompt: str = None, timeout: int = 30) -> str:
    """L2 本地生成 — mini1 Qwen3.5-9B (闲聊/短回复)"""
    cfg = load_config()
    lc_cfg = cfg.get("models", {}).get("local_chat", {})
    url = lc_cfg.get("url", "http://127.0.0.1:8000/v1/chat/completions")
    model = lc_cfg.get("model", "Qwen3.5-9B-MLX-4bit")

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    result = _omlx_request(url, {
        "model": model,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }, timeout=timeout)

    choices = result.get("choices", [])
    return choices[0]["message"]["content"].strip() if choices else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layer 3: 后脑感知 (Qwen3.5-9B, mini2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERCEPTION_PROMPTS = {
    "emotion_classify": (
        "分析以下文本的情感，只输出JSON。\n"
        "格式: {{\"emotion\": \"positive/negative/neutral\", \"intensity\": 0.0-1.0}}\n"
        "文本: {text}"
    ),
    "memory_keyword_extract": (
        "从以下文本中提取3-5个关键词，只输出JSON数组。\n"
        "格式: [\"关键词1\", \"关键词2\", ...]\n"
        "文本: {text}"
    ),
    "intent_classify": (
        "判断以下用户输入的意图类别，只输出一个标签。\n"
        "类别: greeting/quant_analysis/xhs_content/video/coding/question/task/chat/system\n"
        "输入: {text}\n"
        "意图:"
    ),
    "format_quick_check": (
        "检查以下回复是否有格式问题，只输出JSON。\n"
        "格式: {{\"ok\": true/false, \"issue\": \"问题描述或null\"}}\n"
        "回复: {text}"
    ),
}


def perceive(text: str, task: str = "emotion_classify", timeout: int = 10) -> str:
    """L3 后脑感知 — mini2 Qwen3.5-9B (短结构化输出)"""
    cfg = load_config()
    p_cfg = cfg.get("models", {}).get("perception", {})
    url = p_cfg.get("url", "http://127.0.0.1:11434/v1/chat/completions")
    model = p_cfg.get("model", "Qwen3.5-9B-MLX-4bit")
    max_tokens = 50

    prompt_template = PERCEPTION_PROMPTS.get(task, PERCEPTION_PROMPTS["emotion_classify"])
    prompt = prompt_template.replace("{text}", text[:500])

    result = _omlx_request(url, {
        "model": model,
        "messages": [
            {"role": "system", "content": "/no_think 只输出JSON，不要解释。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }, timeout=timeout)

    choices = result.get("choices", [])
    return choices[0]["message"]["content"].strip() if choices else ""


def background(prompt: str, max_tokens: int = 2000, timeout: int = 120) -> str:
    """后台离线任务 — mini2 Qwen3.5-9B"""
    cfg = load_config()
    b_cfg = cfg.get("models", {}).get("perception", {})
    url = b_cfg.get("url", "http://127.0.0.1:11434/v1/chat/completions")
    model = b_cfg.get("model", "Qwen3.5-9B-MLX-4bit")

    result = _omlx_request(url, {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }, timeout=timeout)

    choices = result.get("choices", [])
    return choices[0]["message"]["content"].strip() if choices else ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_node_available(node: str = "node2") -> bool:
    """检查节点是否可达"""
    cfg = load_config()
    base_url = cfg.get("cluster", {}).get(node, {}).get("omlx_url", "http://127.0.0.1:11434")
    try:
        req = Request(f"{base_url}/v1/models")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "data" in data
    except Exception:
        return False


def list_models(node: str = "node2") -> list[dict]:
    """列出节点上的模型"""
    cfg = load_config()
    base_url = cfg.get("cluster", {}).get(node, {}).get("omlx_url", "http://127.0.0.1:11434")
    try:
        req = Request(f"{base_url}/v1/models")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", [])
    except Exception:
        return []


def get_node_url(node: str = "node2") -> str:
    cfg = load_config()
    return cfg.get("cluster", {}).get(node, {}).get("omlx_url", "http://127.0.0.1:11434")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# V15 规格兼容别名 (v15-dev-spec.md Task 1.2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def call_classifier(text: str, timeout: int = 8) -> dict:
    """别名: classify() — L1 闪电分类 (mini1 7B)"""
    return classify(text, timeout=timeout)


def call_local_chat(messages: list, max_tokens: int = 500,
                    temperature: float = 0.7, timeout: int = 30) -> str:
    """别名: local_chat() — 本地 9B 生成"""
    return local_chat(messages, max_tokens=max_tokens,
                      temperature=temperature, timeout=timeout)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("V15 集群客户端")
        print("  --test         测试连通性")
        print("  --embed TEXT   测试嵌入")
        print("  --classify TEXT 测试L1分类")
        print("  --chat TEXT    测试本地生成")
        print("  --perceive TEXT 测试感知")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--test":
        cfg = load_config()
        cluster_on = cfg.get("cluster", {}).get("enabled", False)
        if not cluster_on:
            print("ℹ️  集群未启用 (cluster.enabled=false)，单机模式下跳过连通测试")
            sys.exit(0)
        print("🔗 测试集群连通性...")
        reachable = 0
        for node in ["node1", "node2"]:
            ok = is_node_available(node)
            icon = "✅" if ok else "❌"
            print(f"  {icon} {node}: {get_node_url(node)}")
            if ok:
                reachable += 1
                for m in list_models(node):
                    print(f"      📦 {m.get('id', 'unknown')}")
        # 集群已启用但无任何节点可达 → 非零退出，使上层健康检查能真实发现故障
        if reachable == 0:
            print("❌ 集群已启用但所有节点不可达")
            sys.exit(1)

    elif cmd == "--embed" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        t0 = time.time()
        vec = embed(text)
        dt = (time.time() - t0) * 1000
        print(f"维度: {len(vec)}, 耗时: {dt:.0f}ms")
        if vec:
            print(f"前5维: {vec[:5]}")

    elif cmd == "--classify" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        t0 = time.time()
        result = classify(text)
        dt = (time.time() - t0) * 1000
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"耗时: {dt:.0f}ms")

    elif cmd == "--chat" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        t0 = time.time()
        result = local_chat([{"role": "user", "content": text}])
        dt = (time.time() - t0) * 1000
        print(result)
        print(f"\n耗时: {dt:.0f}ms")

    elif cmd == "--perceive" and len(sys.argv) > 2:
        text = " ".join(sys.argv[2:])
        for task in ["emotion_classify", "intent_classify", "memory_keyword_extract"]:
            t0 = time.time()
            result = perceive(text, task=task)
            dt = (time.time() - t0) * 1000
            print(f"[{task}] {result} ({dt:.0f}ms)")
