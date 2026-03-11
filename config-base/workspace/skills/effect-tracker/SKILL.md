---
name: effect-tracker
triggers: 
version: 1.0.0
description: |
status: stable
platform: [darwin, linux]
dependencies: 
skills: [knowledge-graph-memory]
bins: [python3]
metadata: 
openclaw: 
emoji: "📊"
updated: 2026-03-11
provides: ["effect_tracker"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Effect Tracker 📊

统一的技能效果追踪与度量系统。

## 核心指标

### 技能执行指标

| 指标 | 说明 | 采集方式 |
|------|------|---------|
| `invocation_count` | 调用次数 | 自动计数 |
| `success_rate` | 成功率 | 退出码判定 |
| `avg_latency_ms` | 平均耗时 | 自动计时 |
| `p95_latency_ms` | P95 耗时 | 自动计时 |
| `error_types` | 错误类型分布 | 错误日志分析 |
| `resource_cost` | 资源消耗(API调用/token数) | 自动统计 |

### 业务效果指标

| 指标 | 适用技能 | 说明 |
|------|---------|------|
| `content_quality_score` | xhs-creator, content-empire | 质检评分均值 |
| `publish_success_rate` | xhs-publisher, multi-platform-publisher | 发布成功率 |
| `engagement_rate` | content-empire | 互动率(点赞+收藏+评论/阅读) |
| `signal_accuracy` | quant-strategy-engine | 信号准确率(回测验证) |
| `research_depth_score` | auto-researcher | 信息源数量×交叉验证率 |
| `reasoning_confidence` | deep-reasoning-chain | 平均置信度 |
| `kg_growth_rate` | knowledge-graph-memory | 知识图谱日增实体数 |

---

## 数据存储

```
~/.openclaw/logs/
├── effect-tracker.sqlite     # 效果追踪数据库
└── daily/
    ├── 2026-03-05.jsonl      # 每日原始事件日志
    └── ...
```

### 数据模型

```sql
CREATE TABLE skill_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    skill_name TEXT NOT NULL,
    action TEXT,                    -- 具体操作
    status TEXT NOT NULL,           -- ok/warn/fail
    latency_ms INTEGER,
    tokens_used INTEGER,
    api_calls INTEGER,
    error_type TEXT,
    error_message TEXT,
    metadata JSON                   -- 技能特定的额外指标
);

CREATE TABLE daily_summary (
    date TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    invocations INTEGER,
    successes INTEGER,
    failures INTEGER,
    avg_latency_ms REAL,
    p95_latency_ms REAL,
    total_tokens INTEGER,
    total_api_calls INTEGER,
    business_metrics JSON,          -- 业务指标快照
    PRIMARY KEY (date, skill_name)
);
```

---

## 使用方式

### 记录事件（技能内部调用）

```python
from effect_tracker import track

# 装饰器方式（推荐）
@track("xhs-creator", action="create_note")
def create_note(topic):
    ...

# 手动方式
with track("quant-strategy-engine", action="generate_signal") as t:
    signals = generate_signals()
    t.set_metadata({"signal_count": len(signals)})
```

### 查询效果

```bash
# 今日概览
python3 scripts/tracker.py today

# 某技能最近7天
python3 scripts/tracker.py --skill "xhs-creator" --days 7

# 全部技能报告
python3 scripts/tracker.py report --period weekly

# 失败分析
python3 scripts/tracker.py failures --days 30 --top 10
```

### 报告输出

```bash
# 周报
python3 scripts/tracker.py report --period weekly --format markdown

# 月报（含趋势图）
python3 scripts/tracker.py report --period monthly --format html --charts

# 发送到飞书
python3 scripts/tracker.py report --period weekly --send feishu
```

---

## 报告示例

```markdown
# 📊 OpenClaw 周报 (2026-03-01 ~ 2026-03-07)

## 概览
- 总调用: 1,234 次 (↑12% vs 上周)
- 成功率: 96.8% (↑0.5%)
- 平均延迟: 2.3s (↓0.2s)

## Top 5 活跃技能
| 技能 | 调用 | 成功率 | 平均延迟 |
|------|------|--------|---------|
| xhs-creator | 312 | 98% | 15.2s |
| multi-search-engine | 289 | 95% | 3.1s |
| deep-reasoning-chain | 156 | 99% | 8.7s |
| quant-strategy-engine | 89 | 94% | 12.3s |
| auto-researcher | 45 | 91% | 45.6s |

## 失败热点
| 错误类型 | 次数 | 主要技能 |
|---------|------|---------|
| API超时 | 18 | multi-search-engine |
| Cookie过期 | 12 | xhs-publisher |
| 数据源不可用 | 5 | a-share-real-time-data |

## 业务效果
- 小红书: 发布 21 篇, 平均质检 8.3 分, 平均阅读 1,234
- 研究报告: 生成 8 份, 平均深度评分 7.8
- 量化信号: 生成 45 个, 回测准确率 62%

## 趋势
[success_rate_trend.png]
[latency_trend.png]
```

---

## 告警集成

与 `real-time-sentinel` 联动：

```yaml
effect_alerts:
  - condition: "skill.success_rate < 0.9 over 1h"
    level: warning
    message: "{skill} 成功率降至 {rate}%"
    
  - condition: "skill.avg_latency > skill.p95_latency_baseline * 2"
    level: warning
    message: "{skill} 延迟异常: {latency}ms (基线 {baseline}ms)"
    
  - condition: "skill.consecutive_failures >= 3"
    level: alert
    message: "{skill} 连续失败 {count} 次"
```

---

## 健康检查

```bash
python3 scripts/tracker.py --check
# 检查: SQLite 数据库可读写
# 检查: 日志目录可写
# 检查: 最近事件时间戳（判断是否在正常采集）
```

---

_版本: 1.0.0_  
_创建时间: 2026-03_
