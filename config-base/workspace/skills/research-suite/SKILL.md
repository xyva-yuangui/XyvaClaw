---
name: research-suite
description: Perplexity级融合深度搜索引擎 v3。7层流水线: 意图分析→5源并行搜索(Jina+DDG+Tavily+Brave+SearXNG)→全文深度提取→权威排序+域名多样性→结构化LLM合成(引用+矛盾分析)→跟进问题→迭代深化。
version: 3.0.0
status: stable
updated: 2026-04-14
category: search
provides: ["web_search", "deep_search", "news_search"]
os: ["darwin", "linux"]
triggers:
  - 搜索
  - 搜一下
  - 查一下
  - 帮我找
  - search
  - 最新消息
  - 新闻
  - 调研
metadata:
  openclaw:
    emoji: "🔍"
    category: search
    priority: 90
allowed-tools: Bash(research-suite:*), Bash(python:*), Bash(pip:*)
---

# 🔍 Research Suite v3.0 — Perplexity 级融合深度搜索引擎

7 层流水线，从意图分析到迭代深化，对标 Perplexity AI。

## 架构 (v3.0)

```
L1: 意图分析 + 查询改写 (LLM, 中英文多角度)
L2: 5源并行搜索: Jina Search(免费主力) + DDG(兜底) + Tavily(付费) + Brave(免费) + SearXNG(自建)
L3: 全文深度提取 (Top 8-12, 15K-20K字/篇): Jina Reader → Trafilatura → Fallback
L4: 来源去重 + 权威排序 (20+权威域名) + 域名多样性 (每域名≤3条)
L5: 结构化LLM合成: 核心回答 → 详细分析(带[1][2]引用) → 矛盾分析 → 局限性
L6: 跟进问题生成 (3个延伸方向)
L7: (deep) 迭代深化: 质量评估 → 缺口识别 → 追加搜索 → 重新合成
```

## 使用

```bash
# 标准搜索 (Tavily+DDG, 提取5篇全文, LLM合成)
python3 scripts/search.py --query "AI Agent 最新进展"

# 快速搜索 (仅Tavily, 不抓全文, 1-3s)
python3 scripts/search.py --query "今天A股行情" --depth quick

# 深度搜索 (全部引擎, 提取8篇, LLM深度合成)
python3 scripts/search.py --query "2026新能源汽车格局" --depth deep

# 新闻搜索
python3 scripts/search.py --query "半导体" --type news

# JSON 输出 (供其他技能调用)
python3 scripts/search.py --query "..." --json

# 健康检查
python3 scripts/search.py --check
```

## 搜索深度

| 深度 | 搜索源 | 全文提取 | LLM合成 | 迭代 | 耗时 |
|------|--------|----------|---------|------|------|
| quick | Jina+DDG | 否 | 否 | 否 | 1-3s |
| standard | Jina+DDG+Tavily+Brave | Top 8 (15K字) | 结构化引用 | 否 | 8-20s |
| deep | 全部5源 | Top 12 (20K字) | 深度引用+矛盾 | 质量评估+追加 | 20-60s |

## 替代关系

| 旧技能 | 状态 | 说明 |
|--------|------|------|
| duckduckgo-search | 已吸收 | 降级为兜底搜索后端 |
| auto-researcher | 搜索层替换 | 保留研究编排，搜索改用本技能 |
| multi-search-engine | 已替代 | 从未实现，已被本技能完全替代 |
| web-scraper | 保留 | 非搜索场景仍需 |
| browser-pilot | 保留 | 交互式浏览仍需 |

## 配置

openclaw.json → `search` 段 (所有 API key 均可选，Jina+DDG 免费无需配置):
```json
{
  "search": {
    "tavily": { "apiKey": "tvly-..." },
    "brave": { "apiKey": "BSA..." },
    "searxng": { "baseUrl": "http://localhost:8888", "enabled": false }
  }
}
```

## v3.0 vs v2.0 升级要点
- 主力搜索从 Tavily(付费) 改为 Jina Search(免费), 无API key也能正常工作
- 新增 Brave Search 后端 (免费2000次/月)
- 全文提取深度 8K→15K-20K 字, 提取页数 5→8-12
- 搜索引擎并行化 (ThreadPool 6 workers)
- LLM 合成结构化: 核心回答→详细分析→矛盾→局限性→延伸问题
- deep 模式增加迭代深化: 评估回答质量→识别缺口→追加搜索
- 域名多样性控制: 同域名≤3条, 防止单一来源主导
- 权威来源扩展至 20+ 域名
