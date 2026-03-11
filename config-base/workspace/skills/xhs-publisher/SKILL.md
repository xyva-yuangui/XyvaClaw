---
name: xhs-publisher
version: 1.0.0
description: |
triggers: 
status: stable
platform: [darwin, linux]
dependencies: 
skills: [xhs-creator]
bins: [python3]
python: [requests, websockets, playwright]
metadata: 
openclaw: 
emoji: "🚀"
updated: 2026-03-11
provides: ["xhs_publisher"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# xhs-publisher

小红书统一发布引擎。**触发后必须先询问用户确认**，再执行发布操作。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 单篇发布 | 确认标题、内容、图片数、发布时间 |
| 批量发布 | 确认篇数、主题、风格、发布间隔 |
| CDP 发布 | 确认登录状态、发布通道 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行发布 → 记录结果

Full docs: read SKILL-REFERENCE.md
