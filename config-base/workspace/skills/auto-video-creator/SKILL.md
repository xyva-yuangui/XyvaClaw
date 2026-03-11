---
name: auto-video-creator
description: 自动生成短视频。支持图文轮播、文字动画、卡片风格和 AI 视频大模型生成等多种视频类型。用户需要生成视频时使用此技能。
triggers: 
metadata: 
openclaw: 
emoji: "🎥"
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["video-generation", "media-creation"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🎥", "category": "tools", "priority": "medium"}
---

# Auto Video Creator

视频生成助手。**触发后必须先询问用户确认**，再执行生成。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 图文轮播 | 确认内容源、图片数量、转场效果 |
| 文字动画 | 确认文字内容、动画风格、背景音乐 |
| 卡片视频 | 确认卡片风格、尺寸比例、输出格式 |
| AI 视频生成 | 确认视频描述、时长、风格参考 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行生成 → 返回视频文件

Full docs: read SKILL-REFERENCE.md
