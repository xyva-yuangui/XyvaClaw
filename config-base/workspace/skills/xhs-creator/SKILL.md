---
name: xhs-creator
version: 1.0.0
description: |
triggers: 
status: stable
platform: [darwin, linux]
dependencies: 
skills: [academic-deep-research, content-creator, humanize-ai-text]
bins: [python3]
python: [playwright]
metadata: 
openclaw: 
emoji: "📕"
updated: 2026-03-11
provides: ["xhs_creator"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# xhs-creator

小红书内容创作流水线。**触发后必须先询问用户确认**，再执行创作流程。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 选题创作 | 确认选题方向、风格模板、目标受众 |
| 调研任务 | 确认调研深度、信息来源、输出格式 |
| 制图任务 | 确认卡片数量、主题风格、尺寸比例 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行创作 → 输出素材

Full docs: read SKILL-REFERENCE.md
