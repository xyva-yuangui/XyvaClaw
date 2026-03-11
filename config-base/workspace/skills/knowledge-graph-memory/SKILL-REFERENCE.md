---
name: knowledge-graph-memory
version: 1.0.0
description: |
  知识图谱记忆技能。将对话、文档、研究成果结构化为实体-关系图谱，
  支持关联推理、知识衰减、自动聚合。替代扁平化记忆，实现真正的
  "越用越聪明"。基于 SQLite + JSON，无需外部图数据库。
status: stable
platform: [darwin, linux]
dependencies:
  bins: [python3]
  python: [sqlite3]
metadata:
  openclaw:
    emoji: "🕸️"
---

# Knowledge Graph Memory 🕸️

将 Agent 的记忆从"扁平笔记"升级为"结构化知识图谱"，实现关联推理和知识积累。

## 为什么需要图谱记忆

| 扁平记忆 (现状) | 图谱记忆 (本技能) |
|-----------------|-------------------|
| 线性笔记，搜索靠关键词 | 实体+关系，支持关联查询 |
| 信息孤岛，跨话题无法关联 | 自动发现跨域关联 |
| 记忆无权重，新旧平等 | 知识衰减+强化机制 |
| 手动整理，易过期 | 自动聚合+过期清理 |

---

## 架构

```
用户对话/文档/研究
      ↓
  实体抽取 (Entity Extraction)
      ↓
  关系识别 (Relation Detection)
      ↓
  图谱存储 (SQLite)
      ↓
  查询/推理/聚合
```

### 存储结构

```
~/.openclaw/memory/
├── knowledge-graph.sqlite    # 主图谱数据库
├── embeddings.bin            # 实体向量缓存 (可选)
└── graph-config.yaml         # 图谱配置
```

### 数据模型

```sql
-- 实体表
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,          -- person/company/concept/tool/stock/event/...
    properties JSON,             -- 灵活属性
    confidence REAL DEFAULT 1.0, -- 置信度 0-1
    created_at DATETIME,
    updated_at DATETIME,
    access_count INTEGER DEFAULT 0,
    decay_score REAL DEFAULT 1.0 -- 衰减分数
);

-- 关系表
CREATE TABLE relations (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES entities(id),
    target_id TEXT REFERENCES entities(id),
    type TEXT NOT NULL,           -- uses/owns/related_to/causes/part_of/...
    properties JSON,
    weight REAL DEFAULT 1.0,     -- 关系强度
    evidence TEXT,               -- 证据来源
    created_at DATETIME,
    updated_at DATETIME
);

-- 知识碎片表 (原始来源)
CREATE TABLE fragments (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    source TEXT,                  -- conversation/document/research/...
    source_id TEXT,              -- 来源会话/文档ID
    entities JSON,               -- 关联实体ID列表
    created_at DATETIME
);
```

---

## 核心操作

### 1. 知识摄入 (Ingest)

从对话或文档中自动提取实体和关系：

```bash
# 从文本中提取
python3 scripts/kg.py ingest --text "张三是ABC公司的CEO，该公司使用Python开发AI产品"

# 从文件中提取
python3 scripts/kg.py ingest --file research_report.md

# 从对话历史中提取
python3 scripts/kg.py ingest --conversation session-2026-03-05.json
```

**自动抽取规则**:
- **人名/组织**: 自动识别并创建 person/company 实体
- **工具/技术**: 识别技术栈、工具、框架
- **因果关系**: "因为X所以Y" → X -causes→ Y
- **所属关系**: "A的B" → A -owns→ B
- **使用关系**: "用X做Y" → Y -uses→ X

### 2. 知识查询 (Query)

```bash
# 查找实体
python3 scripts/kg.py query --entity "张三"

# 查找关系
python3 scripts/kg.py query --relation "张三" "uses"

# 关联推理：两个实体之间的路径
python3 scripts/kg.py path --from "Python" --to "ABC公司"

# 邻域探索：某实体的所有关联
python3 scripts/kg.py neighbors --entity "AI" --depth 2

# 自然语言查询
python3 scripts/kg.py ask "张三和什么技术有关？"
```

### 3. 知识强化 (Reinforce)

当知识被再次验证时，增强权重：

```bash
# 手动强化
python3 scripts/kg.py reinforce --entity "Python" --reason "用户再次提到使用Python"

# 自动强化：被查询的知识自动+1 access_count
```

### 4. 知识衰减 (Decay)

长期未被访问的知识自动降权：

```bash
# 执行衰减（建议每日 cron）
python3 scripts/kg.py decay

# 清理低分知识（decay_score < 0.1）
python3 scripts/kg.py prune --threshold 0.1
```

**衰减公式**: `decay_score = initial_score × e^(-λ × days_since_last_access)`
- λ = 0.01 (默认，约 230 天半衰期)
- 每次访问重置 `updated_at`

### 5. 知识聚合 (Aggregate)

自动发现和合并重复/相似实体：

```bash
# 检测可合并实体
python3 scripts/kg.py find-duplicates

# 合并实体
python3 scripts/kg.py merge --ids "entity_1" "entity_2" --keep "entity_1"

# 自动聚合报告
python3 scripts/kg.py aggregate-report
```

---

## 图谱统计

```bash
# 概览
python3 scripts/kg.py stats

# 输出示例:
# Entities: 1,234 (person: 89, company: 45, concept: 312, tool: 156, ...)
# Relations: 3,456
# Fragments: 567
# Avg decay score: 0.72
# Most connected: "Python" (89 relations)
# Most accessed: "OpenClaw" (156 accesses)
```

---

## 与其他技能联动

| 场景 | 联动方式 |
|------|---------|
| 对话结束 | 自动提取本次对话的实体+关系 |
| 研究完成 | academic-deep-research 结果自动入图 |
| 推理分析 | deep-reasoning-chain 查询图谱辅助推理 |
| 新闻监控 | real-time-sentinel 的新闻事件自动入图 |
| 报告生成 | 从图谱自动生成知识总结报告 |

### Agent 自动集成

在 Agent 的每次会话中：
1. **会话开始**: 加载与当前话题相关的图谱知识
2. **会话进行**: 实时提取新知识碎片
3. **会话结束**: 批量写入图谱 + 执行去重

---

## 配置

`graph-config.yaml`:

```yaml
storage:
  path: "~/.openclaw/memory/knowledge-graph.sqlite"
  max_entities: 100000
  max_relations: 500000

extraction:
  auto_ingest: true              # 自动从对话提取
  min_confidence: 0.6            # 最低置信度阈值
  entity_types:                  # 支持的实体类型
    - person
    - company
    - concept
    - tool
    - stock
    - event
    - location
    - document

decay:
  enabled: true
  lambda: 0.01                   # 衰减系数
  prune_threshold: 0.05          # 低于此分数自动清理
  schedule: "daily"              # 衰减执行频率

dedup:
  auto_merge: false              # 自动合并（谨慎开启）
  similarity_threshold: 0.85     # 相似度阈值
```

---

## 健康检查

```bash
python3 scripts/kg.py --check
# 检查: SQLite 数据库可读写
# 检查: 配置文件存在且有效
# 检查: 实体数量/关系数量
# 检查: 衰减任务是否正常运行
```

---

## 注意事项

1. **隐私**: 图谱数据纯本地存储，不上传
2. **性能**: SQLite 单文件，百万级实体查询 <100ms
3. **备份**: 建议定期备份 `knowledge-graph.sqlite`
4. **衰减**: 重要知识通过高频访问自然保留，无需手动维护
5. **去重**: 自动合并建议人工确认，避免误合并

---

_版本: 1.0.0_  
_创建时间: 2026-03_
