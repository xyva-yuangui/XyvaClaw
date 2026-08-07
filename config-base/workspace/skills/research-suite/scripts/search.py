#!/usr/bin/env python3
"""
Research Suite v3.0 — Perplexity 级融合深度搜索引擎

流水线:
  L1: 意图分析 + 查询改写 (LLM)
  L2: 多源并行搜索 (Jina Search + Tavily + DDG + SearXNG + Brave)
  L3: 全文深度提取 (Jina Reader → Trafilatura → Fallback, 并行)
  L4: 来源去重 + 权威排序 + 域名多样性
  L5: 结构化 LLM 合成 (分段推理 + 引用 + 矛盾分析)
  L6: 跟进问题生成 + 质量自检
  L7: (deep) 迭代深化 — 若首轮回答不充分，自动追加搜索

用法:
  python3 search.py --query "AI Agent 最新进展"
  python3 search.py --query "..." --depth quick|standard|deep
  python3 search.py --query "..." --type news
  python3 search.py --query "..." --json
  python3 search.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import re as _re
import sys
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# ── 路径 & 常量 ──
OPENCLAW_HOME = Path(os.path.expanduser("~/.openclaw"))
OPENCLAW_CFG = OPENCLAW_HOME / "openclaw.json"
OUTPUT_DIR = OPENCLAW_HOME / "output" / "search"
JINA_READER = "https://r.jina.ai"
JINA_SEARCH = "https://s.jina.ai"
VERSION = "3.0.0"

# 按深度配置
DEPTH_CFG = {
    "quick":    {"queries": 1, "max_per_engine": 5,  "extract_n": 0,
                 "extract_chars": 0,     "synthesis": False, "iterate": False},
    "standard": {"queries": 3, "max_per_engine": 8,  "extract_n": 8,
                 "extract_chars": 15000, "synthesis": True,  "iterate": False},
    "deep":     {"queries": 5, "max_per_engine": 10, "extract_n": 12,
                 "extract_chars": 20000, "synthesis": True,  "iterate": True},
}
MAX_DOMAIN_RESULTS = 3  # 同一域名最多保留条数


# =====================================================================
# 配置
# =====================================================================

def _load_cfg() -> dict:
    if OPENCLAW_CFG.exists():
        return json.loads(OPENCLAW_CFG.read_text(encoding="utf-8"))
    return {}

def _search_cfg() -> dict:
    return _load_cfg().get("search", {})

def _tavily_key() -> str:
    return _search_cfg().get("tavily", {}).get("apiKey", "")

def _brave_key() -> str:
    return _search_cfg().get("brave", {}).get("apiKey", "") or os.environ.get("BRAVE_API_KEY", "")

def _llm_config() -> tuple:
    """(base_url, model, api_key)"""
    cfg = _load_cfg()
    providers = cfg.get("models", {}).get("providers", {})
    for pname, url, model in [
        ("deepseek", "https://api.deepseek.com/v1", "deepseek-chat"),
        ("bailian", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
    ]:
        p = providers.get(pname, {})
        k = p.get("apiKey", "").strip()
        if k and not k.startswith("sk-sp-"):
            return (p.get("baseUrl", "").strip() or url, model, k)
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return ("https://api.deepseek.com/v1", "deepseek-chat", env_key)
    return ("", "", "")

def _llm_call(prompt: str, max_tokens: int = 4096, temperature: float = 0.3,
              system: str = "") -> str:
    """通用 LLM 调用, 支持 system prompt"""
    base_url, model, api_key = _llm_config()
    if not api_key:
        return ""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = json.dumps({
        "model": model, "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature,
    }).encode()
    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️ LLM: {e}", file=sys.stderr)
        return ""


# =====================================================================
# L1: 意图分析 + 查询改写
# =====================================================================

def analyze_and_rewrite(question: str, num: int = 3) -> dict:
    """LLM 分析搜索意图并改写查询"""
    prompt = f"""分析用户搜索意图，输出 JSON：
{{
  "intent": "factual|comparison|how_to|news|opinion|research",
  "time_sensitive": true/false,
  "queries": ["改写查询1", "改写查询2", ...]
}}

改写要求:
- 共 {num} 条查询词，至少1条中文、1条英文
- 简洁精准，每条≤15词
- 时效性问题加 "{datetime.now().year}" 或 "latest"
- 比较类问题拆成多角度

用户问题: {question}

JSON:"""
    text = _llm_call(prompt, max_tokens=300, temperature=0.2)
    try:
        # 提取 JSON
        m = _re.search(r'\{.*\}', text, _re.S)
        if m:
            parsed = json.loads(m.group())
            queries = parsed.get("queries", [])[:num]
            if queries:
                return {
                    "intent": parsed.get("intent", "research"),
                    "time_sensitive": parsed.get("time_sensitive", False),
                    "queries": queries,
                }
    except Exception:
        pass
    # fallback
    year = datetime.now().year
    return {
        "intent": "research",
        "time_sensitive": False,
        "queries": [question, f"{question} {year}", f"{question} latest"][:num],
    }


# =====================================================================
# L2: 多源搜索 (5 个后端)
# =====================================================================

def _search_jina(query: str, max_results: int = 10) -> list[dict]:
    """Jina Search — 免费搜索 (国内网络可能超时)"""
    try:
        encoded = urllib.parse.quote(query)
        req = urllib.request.Request(
            f"{JINA_SEARCH}/{encoded}",
            headers={"Accept": "application/json",
                     "X-Retain-Images": "none"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Jina 返回 JSON 或 Markdown, 尝试 JSON 优先
        results = []
        try:
            data = json.loads(raw)
            for item in (data.get("data", []) or data.get("results", []))[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": (item.get("description", "") or item.get("content", ""))[:500],
                    "score": 0.8,
                    "source_engine": "jina",
                })
        except json.JSONDecodeError:
            # Markdown 格式解析
            for block in raw.split("\n\n"):
                title_m = _re.search(r'\[([^\]]+)\]\((https?://[^\)]+)\)', block)
                if title_m:
                    results.append({
                        "title": title_m.group(1),
                        "url": title_m.group(2),
                        "snippet": _re.sub(r'\[.*?\]\(.*?\)', '', block).strip()[:500],
                        "score": 0.8,
                        "source_engine": "jina",
                    })
        return results[:max_results]
    except Exception as e:
        print(f"  ⚠️ Jina Search: {e}", file=sys.stderr)
        return []


def _search_tavily(query: str, max_results: int = 10,
                   search_type: str = "text") -> tuple[list[dict], str]:
    """Tavily API — 付费高质量搜索"""
    api_key = _tavily_key()
    if not api_key:
        return [], ""
    topic = "news" if search_type == "news" else "general"
    body = json.dumps({
        "api_key": api_key, "query": query,
        "max_results": max_results, "include_answer": True,
        "include_raw_content": False, "search_depth": "advanced", "topic": topic,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""), "url": r.get("url", ""),
                "snippet": r.get("content", ""), "score": r.get("score", 0.7),
                "source_engine": "tavily",
            })
        return results, data.get("answer", "")
    except Exception as e:
        print(f"  ⚠️ Tavily: {e}", file=sys.stderr)
        return [], ""


def _search_brave(query: str, max_results: int = 10) -> list[dict]:
    """Brave Search API — 免费 2000次/月"""
    api_key = _brave_key()
    if not api_key:
        return []
    params = urllib.parse.urlencode({"q": query, "count": max_results})
    try:
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={"Accept": "application/json",
                     "Accept-Encoding": "gzip",
                     "X-Subscription-Token": api_key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return [{"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": r.get("description", ""), "score": 0.75,
                 "source_engine": "brave"}
                for r in data.get("web", {}).get("results", [])[:max_results]]
    except Exception as e:
        print(f"  ⚠️ Brave: {e}", file=sys.stderr)
        return []


def _search_ddg(query: str, max_results: int = 10,
                search_type: str = "text") -> list[dict]:
    """DuckDuckGo — 免费兜底"""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            return []
    try:
        with DDGS() as ddgs:
            fn = ddgs.news if search_type == "news" else ddgs.text
            return [{"title": r.get("title", ""),
                     "url": r.get("href") or r.get("url", ""),
                     "snippet": r.get("body", ""), "score": 0.5,
                     "source_engine": "ddg"}
                    for r in fn(query, region="cn-zh", max_results=max_results)]
    except Exception as e:
        print(f"  ⚠️ DDG: {e}", file=sys.stderr)
        return []


def _search_searxng(query: str, max_results: int = 10) -> list[dict]:
    """SearXNG 本地元搜索"""
    cfg = _search_cfg().get("searxng", {})
    if not cfg.get("enabled"):
        return []
    base_url = cfg.get("baseUrl", "http://localhost:8888")
    params = urllib.parse.urlencode({"q": query, "format": "json", "language": "zh-CN"})
    try:
        req = urllib.request.Request(f"{base_url}/search?{params}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return [{"title": r.get("title", ""), "url": r.get("url", ""),
                 "snippet": r.get("content", ""), "score": r.get("score", 0.6),
                 "source_engine": f"searxng:{r.get('engine', '')}"}
                for r in data.get("results", [])[:max_results]]
    except Exception as e:
        print(f"  ⚠️ SearXNG: {e}", file=sys.stderr)
        return []


def multi_search(queries: list[str], depth: str = "standard",
                 search_type: str = "text",
                 verbose: bool = False) -> tuple[list[dict], str]:
    """多源并行搜索 + 去重 + 域名多样性"""
    cfg = DEPTH_CFG.get(depth, DEPTH_CFG["standard"])
    n = cfg["max_per_engine"]
    all_results: list[dict] = []
    tavily_answer = ""
    engines_used = []

    def _run_search(fn, *args) -> list[dict]:
        try:
            result = fn(*args)
            return result if isinstance(result, list) else []
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = []
        for q in queries:
            # Tavily 优先 (付费高质量, 稳定)
            if _tavily_key():
                futures.append(("tavily", pool.submit(_search_tavily, q, n, search_type)))
            # DDG 始终使用 (免费兜底)
            futures.append(("ddg", pool.submit(_search_ddg, q, n, search_type)))
            # Jina Search (免费, 但国内网络可能超时)
            futures.append(("jina", pool.submit(_search_jina, q, n)))
            # Brave (如果有 key)
            if _brave_key():
                futures.append(("brave", pool.submit(_search_brave, q, n)))
            # SearXNG (deep 模式)
            if depth == "deep":
                futures.append(("searxng", pool.submit(_search_searxng, q, n)))

        for engine_name, fut in futures:
            try:
                result = fut.result(timeout=20)
                if engine_name == "tavily" and isinstance(result, tuple):
                    items, ans = result
                    all_results.extend(items)
                    if ans and not tavily_answer:
                        tavily_answer = ans
                elif isinstance(result, list):
                    all_results.extend(result)
                if engine_name not in engines_used:
                    engines_used.append(engine_name)
            except Exception:
                pass

    if verbose:
        print(f"  🔌 引擎: {', '.join(engines_used)}")

    # 去重 (URL 标准化)
    seen: set[str] = set()
    unique = []
    for r in all_results:
        url = r.get("url", "").rstrip("/").split("?")[0].split("#")[0]
        if url and url not in seen:
            seen.add(url)
            unique.append(r)

    # 域名多样性: 每个域名最多 MAX_DOMAIN_RESULTS 条
    domain_count: dict[str, int] = {}
    diverse = []
    for r in sorted(unique, key=lambda x: x.get("score", 0), reverse=True):
        domain = urlparse(r.get("url", "")).netloc
        cnt = domain_count.get(domain, 0)
        if cnt < MAX_DOMAIN_RESULTS:
            diverse.append(r)
            domain_count[domain] = cnt + 1

    return diverse, tavily_answer


# =====================================================================
# L3: 全文深度提取
# =====================================================================

def _extract_jina(url: str, max_chars: int) -> str:
    """Jina Reader: URL → Markdown (免费)"""
    try:
        req = urllib.request.Request(
            f"{JINA_READER}/{url}",
            headers={"Accept": "text/markdown", "X-No-Cache": "true",
                     "X-Return-Format": "markdown"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read().decode("utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""

def _extract_trafilatura(url: str, max_chars: int) -> str:
    """Trafilatura 学术级提取"""
    try:
        import trafilatura
        dl = trafilatura.fetch_url(url)
        if dl:
            text = trafilatura.extract(dl, include_comments=False,
                                       include_tables=True, output_format="txt")
            return (text or "")[:max_chars]
    except Exception:
        pass
    return ""

def _extract_fallback(url: str, max_chars: int) -> str:
    """最后手段: urllib + 简易正文提取"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36"
        })
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        html = _re.sub(r"<(script|style|nav|footer|header|aside|noscript)[^>]*>.*?</\1>",
                        "", html, flags=_re.S | _re.I)
        text = _re.sub(r"<[^>]+>", "\n", html)
        lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 30]
        return "\n".join(lines)[:max_chars]
    except Exception:
        return ""

def extract_content(url: str, max_chars: int = 15000) -> str:
    """全文提取: Jina Reader → Trafilatura → Fallback"""
    if not url or not url.startswith("http"):
        return ""
    skip = (".pdf", ".mp4", ".mp3", ".zip", ".rar", ".exe", ".dmg",
            ".doc", ".xls", ".ppt", ".apk", ".iso")
    if any(url.lower().endswith(e) for e in skip):
        return ""

    content = _extract_jina(url, max_chars)
    if content and len(content) > 300:
        return content
    content = _extract_trafilatura(url, max_chars)
    if content and len(content) > 300:
        return content
    return _extract_fallback(url, max_chars)

def extract_batch(results: list[dict], top_n: int = 8,
                  max_chars: int = 15000) -> list[dict]:
    """并行批量提取 Top N 全文"""
    targets = results[:top_n]
    def _do(item):
        c = extract_content(item.get("url", ""), max_chars)
        return item, c
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_do, t): t for t in targets}
        for f in as_completed(futs):
            try:
                item, content = f.result()
                if content:
                    item["full_content"] = content
                    item["content_length"] = len(content)
            except Exception:
                pass
    return results


# =====================================================================
# L4: 排序 + 域名多样性
# =====================================================================

_AUTHORITY = {
    "gov.cn": 1.6, "edu.cn": 1.5, "ac.cn": 1.5, "mil.cn": 1.4,
    "reuters.com": 1.4, "bloomberg.com": 1.4, "ft.com": 1.4,
    "arxiv.org": 1.4, "nature.com": 1.4, "science.org": 1.4,
    "github.com": 1.3, "wikipedia.org": 1.3, "nytimes.com": 1.3,
    "bbc.com": 1.2, "theguardian.com": 1.2,
    "zhihu.com": 1.15, "36kr.com": 1.15, "mp.weixin.qq.com": 1.1,
    "sspai.com": 1.1, "juejin.cn": 1.1, "cnblogs.com": 1.05,
}

def rank_results(results: list[dict]) -> list[dict]:
    for r in results:
        s = r.get("score", 0.5)
        url = r.get("url", "")
        for domain, bonus in _AUTHORITY.items():
            if domain in url:
                s *= bonus
                break
        # 全文加成: 有内容 + 内容越长权重越高
        cl = r.get("content_length", 0)
        if cl > 0:
            s *= (1.0 + min(cl / 15000, 0.6))
        # 标题和摘要的信息密度
        snippet = r.get("snippet", "")
        if len(snippet) > 200:
            s *= 1.1
        r["_rank"] = round(s, 4)
    results.sort(key=lambda x: x.get("_rank", 0), reverse=True)
    return results


# =====================================================================
# L5: 结构化 LLM 合成 (Perplexity 级)
# =====================================================================

SYNTHESIS_SYSTEM = """你是一个专业的深度搜索引擎合成专家，风格类似 Perplexity AI。
你的任务是基于搜索结果为用户生成全面、深入、有引用的回答。"""

def synthesize(question: str, results: list[dict],
               tavily_answer: str = "", intent: str = "research") -> str:
    """LLM 合成带引用的 Perplexity 级结构化回答"""
    # 构建来源文本 — 提供更多内容给 LLM
    sources = []
    total_context_chars = 0
    max_context = 40000  # 给 LLM 的最大上下文
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("full_content", "") or r.get("snippet", "")
        # 按排名分配内容配额: 前3名多给, 后面少给
        quota = 4000 if i <= 3 else (2500 if i <= 6 else 1200)
        if total_context_chars + quota > max_context:
            quota = max(500, max_context - total_context_chars)
        if quota <= 0:
            break
        sources.append(f"[{i}] {title}\nURL: {url}\n{content[:quota]}")
        total_context_chars += min(len(content), quota)

    context = "\n\n---\n\n".join(sources)

    prompt = f"""基于以下 {len(sources)} 个来源，回答用户的搜索问题。

## 输出格式要求

### 核心回答 (2-4句)
直接回答问题的核心要点。

### 详细分析
- 分主题/段落展开，每段有小标题
- 每个关键事实用 [1][2] 等内联引用标注来源编号
- 包含具体数据、日期、人名、机构名
- 如果涉及比较，用表格或对比结构
- 如果来源之间有矛盾，明确指出差异并分析可能原因

### 局限性说明
如果来源不足以完全回答问题，诚实说明哪些方面信息不足。

### 延伸问题
建议 3 个用户可能感兴趣的跟进问题。

### 参考来源
列出引用过的来源: [编号] 标题 — URL

## 规则
- 必须基于来源内容，不编造
- 中文回答，专业准确但通俗易懂
- 回答深度要对得起"深度搜索"的定位 — 不要浮于表面
- 引用格式: 在相关内容后紧跟 [1][2]

用户问题: {question}
搜索意图: {intent}
{"参考摘要: " + tavily_answer[:500] if tavily_answer else ""}

搜索来源:
{context}

请输出完整回答:"""

    answer = _llm_call(prompt, max_tokens=4096, temperature=0.3,
                       system=SYNTHESIS_SYSTEM)
    if not answer:
        return _format_fallback(question, results, tavily_answer)
    return answer


def _format_fallback(question: str, results: list[dict], tavily_answer: str) -> str:
    """无 LLM 时的格式化输出"""
    lines = [f"# 搜索结果: {question}\n"]
    if tavily_answer:
        lines.append(f"**AI 摘要**: {tavily_answer}\n")
    lines.append("## 来源\n")
    for i, r in enumerate(results[:12], 1):
        lines.append(f"### [{i}] {r.get('title', '')}")
        lines.append(f"🔗 {r.get('url', '')}")
        snippet = r.get("snippet", "")
        if snippet:
            lines.append(f"{snippet[:400]}\n")
    return "\n".join(lines)


# =====================================================================
# L7: 迭代深化 (deep 模式)
# =====================================================================

def _assess_answer_quality(question: str, answer: str) -> dict:
    """LLM 评估回答是否充分"""
    prompt = f"""评估这个搜索回答的质量，输出 JSON:
{{
  "sufficient": true/false,
  "score": 1-10,
  "gaps": ["缺少的信息1", "缺少的信息2"],
  "followup_queries": ["补充搜索1", "补充搜索2"]
}}

用户问题: {question}

回答:
{answer[:3000]}

JSON:"""
    text = _llm_call(prompt, max_tokens=300, temperature=0.2)
    try:
        m = _re.search(r'\{.*\}', text, _re.S)
        if m:
            return json.loads(m.group())
    except Exception:
        pass
    return {"sufficient": True, "score": 7, "gaps": [], "followup_queries": []}


# =====================================================================
# 主流程
# =====================================================================

def deep_search(question: str, depth: str = "standard",
                search_type: str = "text", do_synthesis: bool = True,
                verbose: bool = True) -> dict:
    """完整深度搜索流程 v3"""
    t0 = time.monotonic()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = DEPTH_CFG.get(depth, DEPTH_CFG["standard"])

    if verbose:
        print(f"\n🔍 Research Suite v{VERSION}")
        print(f"   问题: {question}")
        print(f"   深度: {depth} | 类型: {search_type}")

    # ── L1: 意图分析 + 查询改写 ──
    if cfg["queries"] <= 1:
        analysis = {"intent": "quick", "time_sensitive": False, "queries": [question]}
    else:
        if verbose:
            print("  📝 L1: 意图分析 + 查询改写...")
        analysis = analyze_and_rewrite(question, cfg["queries"])
    queries = analysis["queries"]
    intent = analysis.get("intent", "research")
    if verbose:
        print(f"  📝 意图: {intent} | 查询: {queries}")

    # ── L2: 多源并行搜索 ──
    if verbose:
        print("  🌐 L2: 多源并行搜索...")
    results, tavily_answer = multi_search(queries, depth, search_type, verbose)
    if verbose:
        print(f"  📊 获取 {len(results)} 条去重结果")
    if tavily_answer and verbose:
        print(f"  💡 Tavily 摘要: {tavily_answer[:80]}...")

    # ── L3: 全文深度提取 ──
    if cfg["extract_n"] > 0 and results:
        if verbose:
            print(f"  📖 L3: 全文提取 (Top {cfg['extract_n']}, 最大{cfg['extract_chars']}字/篇)...")
        results = extract_batch(results, cfg["extract_n"], cfg["extract_chars"])
        extracted = sum(1 for r in results if r.get("full_content"))
        total_chars = sum(r.get("content_length", 0) for r in results)
        if verbose:
            print(f"  📖 成功提取 {extracted} 篇 ({total_chars:,} 字)")

    # ── L4: 排序 ──
    results = rank_results(results)

    # ── L5: 合成 ──
    answer = ""
    if do_synthesis and cfg["synthesis"]:
        if verbose:
            print("  🤖 L5: 结构化 LLM 合成...")
        answer = synthesize(question, results, tavily_answer, intent)
    elif tavily_answer:
        answer = tavily_answer

    # ── L7: 迭代深化 (deep 模式) ──
    iteration_info = None
    if cfg["iterate"] and answer and do_synthesis:
        if verbose:
            print("  🔄 L7: 评估回答质量...")
        assessment = _assess_answer_quality(question, answer)
        if not assessment.get("sufficient", True) and assessment.get("followup_queries"):
            if verbose:
                gaps = assessment.get("gaps", [])
                print(f"  🔄 质量评分: {assessment.get('score', '?')}/10, "
                      f"缺口: {gaps[:2]}")
                print(f"  🔄 追加搜索: {assessment['followup_queries'][:2]}")
            # 追加搜索
            extra_results, _ = multi_search(
                assessment["followup_queries"][:2], "standard", search_type, verbose)
            if extra_results:
                extra_results = extract_batch(extra_results, 4, cfg["extract_chars"])
                results.extend(extra_results)
                results = rank_results(results)
                if verbose:
                    print(f"  🔄 追加 {len(extra_results)} 条来源, 重新合成...")
                answer = synthesize(question, results, tavily_answer, intent)
            iteration_info = assessment

    elapsed = int((time.monotonic() - t0) * 1000)
    if verbose:
        print(f"  ⏱️  总耗时: {elapsed}ms")

    # 保存结果
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"search_{ts}.json"
    output = {
        "version": VERSION,
        "question": question, "depth": depth, "type": search_type,
        "intent": intent,
        "queries": queries, "result_count": len(results),
        "tavily_answer": tavily_answer, "answer": answer,
        "elapsed_ms": elapsed, "timestamp": datetime.now().isoformat(),
        "iteration": iteration_info,
        "sources": [{"title": r.get("title"), "url": r.get("url"),
                     "snippet": r.get("snippet", "")[:300],
                     "source_engine": r.get("source_engine"),
                     "has_full_content": bool(r.get("full_content")),
                     "content_length": r.get("content_length", 0),
                     "rank_score": r.get("_rank", 0)}
                    for r in results[:20]],
    }
    out_file.write_text(json.dumps(output, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    return output


# =====================================================================
# 健康检查
# =====================================================================

def health_check() -> dict:
    checks = []
    # Jina Search (免费, 国内可能超时)
    try:
        _jina_req = urllib.request.Request(
            f"{JINA_SEARCH}/{urllib.parse.quote('test')}",
            headers={"Accept": "application/json"})
        urllib.request.urlopen(_jina_req, timeout=5)
        checks.append({"name": "jina-search", "status": "ok",
                       "message": "s.jina.ai (连通正常)"})
    except Exception:
        checks.append({"name": "jina-search", "status": "warn",
                       "message": "s.jina.ai 超时 (国内网络限制, 自动降级)"})
    # DDG
    try:
        from duckduckgo_search import DDGS
        checks.append({"name": "duckduckgo-search", "status": "ok",
                       "message": "duckduckgo_search (建议迁移到 ddgs)"})
    except ImportError:
        try:
            from ddgs import DDGS
            checks.append({"name": "duckduckgo-search", "status": "ok",
                           "message": "ddgs (新包名)"})
        except ImportError:
            checks.append({"name": "duckduckgo-search", "status": "warn",
                           "message": "pip install ddgs"})
    # Tavily (可选付费)
    key = _tavily_key()
    checks.append({"name": "tavily-api", "status": "ok" if key else "info",
                   "message": "" if key else "未配置 (可选, search.tavily.apiKey)"})
    # Brave (可选免费)
    bk = _brave_key()
    checks.append({"name": "brave-search", "status": "ok" if bk else "info",
                   "message": "" if bk else "未配置 (可选, search.brave.apiKey)"})
    # Trafilatura
    try:
        import trafilatura
        checks.append({"name": "trafilatura", "status": "ok"})
    except ImportError:
        checks.append({"name": "trafilatura", "status": "warn",
                       "message": "pip install trafilatura lxml_html_clean"})
    # Jina Reader
    checks.append({"name": "jina-reader", "status": "ok",
                   "message": "r.jina.ai (免费, 全文提取)"})
    # LLM
    _, _, api_key = _llm_config()
    checks.append({"name": "llm-synthesis", "status": "ok" if api_key else "warn",
                   "message": "" if api_key else "缺少 LLM API key"})
    # SearXNG
    searxng = _search_cfg().get("searxng", {})
    if searxng.get("enabled"):
        try:
            urllib.request.urlopen(searxng.get("baseUrl", "http://localhost:8888"),
                                  timeout=3)
            checks.append({"name": "searxng", "status": "ok"})
        except Exception:
            checks.append({"name": "searxng", "status": "warn",
                           "message": "SearXNG 不可达"})
    else:
        checks.append({"name": "searxng", "status": "info",
                       "message": "未启用 (可选)"})

    fail = any(c["status"] == "fail" for c in checks)
    warn = any(c["status"] == "warn" for c in checks)
    overall = "fail" if fail else ("warn" if warn else "ok")
    return {"skill": "research-suite", "version": VERSION,
            "status": overall, "checks": checks,
            "timestamp": datetime.now().isoformat()}


# =====================================================================
# CLI
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description=f"Research Suite v{VERSION} — Perplexity 级融合深度搜索引擎")
    parser.add_argument("--query", "-q", help="搜索问题")
    parser.add_argument("--depth", "-d", choices=["quick", "standard", "deep"],
                        default="standard", help="搜索深度")
    parser.add_argument("--type", "-t", choices=["text", "news"], default="text")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--no-synthesis", action="store_true", help="不做 LLM 合成")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    if not args.query:
        parser.print_help()
        sys.exit(0)

    result = deep_search(args.query, args.depth, args.type,
                         do_synthesis=not args.no_synthesis,
                         verbose=not args.as_json)

    if args.as_json:
        print(json.dumps({
            "question": result["question"],
            "answer": result["answer"],
            "intent": result.get("intent"),
            "source_count": result["result_count"],
            "elapsed_ms": result["elapsed_ms"],
            "sources": result["sources"][:8],
        }, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 70)
        if result.get("answer"):
            print(result["answer"])
        print("\n📚 参考来源:")
        for i, s in enumerate(result.get("sources", [])[:10], 1):
            icon = "📄" if s.get("has_full_content") else "📋"
            cl = s.get("content_length", 0)
            info = f" ({cl:,}字)" if cl else ""
            print(f"  {icon} [{i}] {s['title'][:60]}{info}")
            print(f"       {s['url']}")
        print(f"\n⏱️  {result['elapsed_ms']}ms | 🔗 {result['result_count']} 条来源 "
              f"| 意图: {result.get('intent', '?')}")
        if result.get("iteration"):
            print(f"🔄 迭代深化: 评分 {result['iteration'].get('score', '?')}/10")
        print("=" * 70)


if __name__ == "__main__":
    main()
