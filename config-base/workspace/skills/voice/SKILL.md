---
name: voice
description: 语音对话能力。支持语音合成(TTS)和语音识别(STT)。TTS 使用 edge-tts（免费），STT 使用 Whisper API 或本地 whisper.cpp。用户需要语音输入/输出时使用此技能。
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-15
provides: ["voice", "tts", "stt"]
os: ["darwin", "linux"]
clawdbot: {"emoji": "🎙️", "category": "tools", "priority": "medium"}
---

# Voice — 语音对话

语音合成 (TTS) + 语音识别 (STT) 统一技能。

## 功能

### TTS（文字转语音）
- **引擎**：edge-tts（微软免费 TTS，200+ 语音）
- **输出格式**：MP3 / WAV / OGG
- **支持语言**：中文、英文、日文、韩文等 50+ 语言

### STT（语音转文字）
- **方式 1**：OpenAI Whisper API（需 API Key，速度快）
- **方式 2**：本地 whisper.cpp（离线，需下载模型）
- **支持格式**：MP3 / WAV / M4A / OGG / FLAC

## 使用方式

```bash
# 健康检查
python3 scripts/check.py

# TTS: 文字转语音
python3 scripts/voice_tool.py tts --text "你好，我是你的AI助手" --output hello.mp3
python3 scripts/voice_tool.py tts --text "Hello world" --voice en-US-AriaNeural --output hello.mp3

# TTS: 列出可用语音
python3 scripts/voice_tool.py tts-voices --lang zh

# STT: 语音转文字（Whisper API）
python3 scripts/voice_tool.py stt --input audio.mp3
python3 scripts/voice_tool.py stt --input audio.mp3 --lang zh

# STT: 语音转文字（本地 whisper.cpp）
python3 scripts/voice_tool.py stt --input audio.mp3 --engine local
```

## 配置

- TTS 无需配置，开箱即用
- STT Whisper API 需设置 `OPENAI_API_KEY` 环境变量
- STT 本地模式需安装 whisper.cpp 并下载模型

## 输出目录

`$OPENCLAW_HOME/workspace/output/audio/`

## 依赖

- edge-tts (`pip3 install edge-tts`) — 安装脚本已自动安装
- openai (`pip3 install openai`) — STT API 模式可选
