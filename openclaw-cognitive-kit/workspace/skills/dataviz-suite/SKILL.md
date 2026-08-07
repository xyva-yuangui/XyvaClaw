---
name: dataviz-suite
description: 数据可视化套件。图表生成→数据分析可视化→架构图/流程图绘制的统一可视化工具。
version: 1.0.0
status: stable
updated: 2026-04-01
category: visualization
provides: ["chart_generation", "data_visualization", "diagram_generation"]
os: ["darwin", "linux"]
triggers:
metadata:
  openclaw:
    emoji: "📊"
    category: visualization
    priority: 65
---

# DataViz Suite — 数据可视化套件

## 子模块路由

| 意图 | 子模块 | 原 Skill |
|------|--------|----------|
| data_visualization (柱状图/折线图/饼图) | `python-dataviz` + `chart-image` | python-dataviz, chart-image |
| diagram (架构图/流程图/思维导图) | `diagram-generator` | diagram-generator |

## 路由逻辑

1. 数据驱动的图表（有数据集）→ python-dataviz
2. 静态图表图片 → chart-image
3. 架构图/流程图/ER图 → diagram-generator
