---
name: auto-researcher
triggers: 
version: 1.0.0
description: |
status: stable
platform: [darwin, linux]
dependencies: 
skills: [multi-search-engine, academic-deep-research, web-scraper, deep-reasoning-chain, knowledge-graph-memory, python-dataviz]
bins: [python3]
metadata: 
openclaw: 
emoji: "🔬"
updated: 2026-03-11
provides: ["auto_researcher"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# 🔬  🔬  Auto Researcher 🔬

**重要**: 触发后必须先询问用户确认，再执行操作。


**重要**: 触发后必须先询问用户确认，再执行操作。


全自动深度研究引擎：给定主题，自动完成从信息搜集到报告输出的全流程。

## 核心流程

```
主题输入 → 问题分解 → 多轮搜索 → 信息提取 → 交叉验证 → 知识入库 → 报告生成
    ↑                                                              |
    └──────────────── 发现子问题，自动追问 ←────────────────────────┘
```

---

# 🔬  🔬 # 快速开始

```bash
# 基础研究
python3 scripts/researcher.py --topic "2026年中国新能源汽车市场竞争格局"

# 深度研究（更多轮次、更多来源）
python3 scripts/researcher.py --topic "AI Agent 架构演进" --depth deep

# 指定输出格式
python3 scripts/researcher.py --topic "量化选股策略对比" --format feishu-doc

# 中英文混合研究
python3 scripts/researcher.py --topic "全球半导体供应链风险" --langs "zh,en"

# 恢复中断的研究
python3 scripts/researcher.py --resume session-20260305-abc123
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--topic` | 研究主题 | 必填 |
| `--depth` | 研究深度: quick/standard/deep | standard |
| `--format` | 输出格式: markdown/html/feishu-doc/pdf | markdown |
| `--langs` | 搜索语言 | zh,en |
| `--max-rounds` | 最大搜索轮次 | 5 (deep=10) |
| `--max-sources` | 最大信息源数量 | 20 (deep=50) |
| `--output` | 输出目录 | ./output/research/ |
| `--resume` | 恢复之前的研究会话 | - |
| `--check` | 健康检查 | - |

---

# 🔬  🔬 # 研究深度对比

| 维度 | quick (5min) | standard (15min) | deep (30min+) |
|------|-------------|-----------------|---------------|
| 搜索轮次 | 1-2 | 3-5 | 5-10 |
| 信息源 | 5-10 | 10-20 | 20-50 |
| 交叉验证 | 基础 | 标准 | 严格+多语言 |
| 子问题追问 | 无 | 1 层 | 2-3 层递归 |
| 报告字数 | 500-1000 | 2000-5000 | 5000-15000 |
| 图表 | 无 | 1-2 张 | 3-5 张 |

---

# 🔬  🔬 # 研究流程详解

### Step 1: 问题分解

```
原始主题: "2026年中国新能源汽车市场竞争格局"
    ↓
子问题:
├── Q1: 2026年中国新能源汽车销量和市场份额数据？
├── Q2: 主要竞争者（比亚迪/特斯拉/蔚来...）最新动态？
├── Q3: 政策环境变化（补贴/碳积分/出口）？
├── Q4: 技术趋势（固态电池/智驾/充电）？
└── Q5: 海外市场拓展情况？
```

使用 `deep-reasoning-chain` 进行问题拆解，确保覆盖全面。

### Step 2: 多轮搜索

每个子问题独立搜索，使用 `multi-search-engine` 多引擎并行：

```
Q1 → Google + Bing + 百度 → 结果集 R1
Q2 → Google + Reddit + 微信搜索 → 结果集 R2
Q3 → Google + 政府网站 → 结果集 R3
...
```

**搜索策略**:
- 每个子问题生成 3-5 个不同角度的搜索词
- 中英文同时搜索（`--langs` 控制）
- 自动过滤低质量来源（广告、SEO 垃圾）
- 优先权威来源（政府、学术、行业报告）

### Step 3: 信息提取

使用 `web-scraper` 提取搜索结果的核心内容：

- 自动提取正文，去除导航/广告/侧边栏
- 提取关键数据点（数字、日期、比较）
- 提取引用和来源标注
- 对每条信息标注可信度（基于来源权威性）

### Step 4: 交叉验证

使用 `deep-reasoning-chain` 进行多源交叉验证：

```
信息点 X:
  来源 1 (路透社): "比亚迪2025年销量突破400万"  置信度: 0.95
  来源 2 (公司财报): "全年销量389.5万"          置信度: 0.99
  来源 3 (自媒体): "销量超500万"                置信度: 0.30
  → 综合结论: 约390-400万 (高置信)
  → 标注来源 3 为不可靠
```

### Step 5: 知识入库

将研究成果结构化后存入 `knowledge-graph-memory`:

- 实体：公司、人物、技术、政策、数据点
- 关系：竞争、供应、投资、因果
- 下次研究相同领域时自动调用已有知识

### Step 6: 报告生成

**报告结构**:

```markdown
# 📊 研究报告：[主题]

## 执行摘要
[3-5 句话总结核心发现]

## 关键发现
1. [发现 1] — 置信度: 高
2. [发现 2] — 置信度: 中
3. [发现 3] — 置信度: 高

## 详细分析
### [子问题 1]
[分析内容 + 数据 + 图表]
### [子问题 2]
...

## 数据图表
[自动生成的可视化]

## 风险与不确定性
[标注低置信度的部分]

## 参考来源
[所有引用来源列表，标注可信度]

---
研究参数: depth=standard, rounds=4, sources=18
生成时间: 2026-03-05 10:30
```

---

# 🔬  🔬 # 自动追问机制

研究过程中发现的新问题自动纳入搜索队列：

```
初始问题: "AI Agent 架构"
  → 搜索发现 "MCP 协议" 是新趋势
  → 自动生成子问题: "MCP 协议的技术细节和应用案例？"
  → 执行新一轮搜索
  → 合并到最终报告
```

**递归深度限制**:
- quick: 不追问
- standard: 1 层 (最多追加 3 个子问题)
- deep: 2-3 层 (最多追加 10 个子问题)

---

# 🔬  🔬 # 可中断恢复

长时间研究任务自动保存进度：

```
~/.openclaw/workspace/output/research/
└── session-20260305-abc123/
    ├── state.json           # 研究状态（已完成的步骤、队列）
    ├── raw/                 # 原始搜索结果
    ├── extracted/           # 提取的信息
    ├── report.md            # 最终报告（持续更新）
    └── graph-updates.json   # 待入库的知识图谱更新
```

中断后恢复：`python3 scripts/researcher.py --resume session-20260305-abc123`

---

# 🔬  🔬 # 输出格式

| 格式 | 说明 | 用途 |
|------|------|------|
| `markdown` | 标准 Markdown | 本地阅读/版本控制 |
| `html` | 带样式的 HTML | 分享/打印 |
| `feishu-doc` | 飞书文档（自动创建） | 团队协作 |
| `pdf` | PDF 导出 | 正式报告 |

---

# 🔬  🔬 # 注意事项

1. **真实性**: 所有数据必须有来源，不可编造
2. **时效性**: 标注信息的时间，区分历史数据和最新数据
3. **偏见控制**: 多源搜索避免单一来源偏见
4. **隐私**: 搜索内容不上传到第三方，结果本地存储
5. **合规**: 尊重网站 robots.txt 和使用条款

---

_版本: 1.0.0_  
_创建时间: 2026-03_
