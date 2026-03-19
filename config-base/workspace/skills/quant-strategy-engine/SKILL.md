---
name: quant-strategy-engine
version: 1.0.0
description: |
triggers: 
status: stable
platform: [darwin, linux]
dependencies: 
skills: [a-share-real-time-data, deep-reasoning-chain, real-time-sentinel, python-dataviz]
bins: [python3]
python: [pandas, numpy, mootdx, ta]
metadata: 
openclaw: 
emoji: "📈"
updated: 2026-03-11
provides: ["quant_strategy_engine"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# quant-strategy-engine

量化策略引擎。**触发后必须先询问用户确认**，再执行策略分析。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 策略选股 | 确认选股范围 (全市场/板块)、因子类型、持仓周期 |
| 因子分析 | 确认因子类别 (估值/动量/质量)、时间窗口、可视化需求 |
| 策略回测 | 确认回测区间、初始资金、手续费率、调仓频率 |
| 信号生成 | 确认信号类型 (买入/卖出/预警)、推送方式 |
| 风控管理 | 确认止损线、仓位上限、风险敞口 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行分析 → 输出报告

Full docs: read SKILL-REFERENCE.md
