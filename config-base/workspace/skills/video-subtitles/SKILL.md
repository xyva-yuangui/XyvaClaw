---
name: video-subtitles
description: Generate SRT subtitles from video/audio with translation support. Transcribes Chinese (FunASR/Whisper), English (Whisper), Hebrew (ivrit.ai), translates between languages, burns subtitles into video. Use for creating captions, transcripts, or hardcoded subtitles.
triggers: 
metadata: 
openclaw: 
emoji: "🎬"
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["video-generation", "media-creation"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🎥", "category": "tools", "priority": "medium"}
---

# Video Subtitles

字幕生成助手。**触发后必须先询问用户确认**，再执行生成。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 字幕生成 | 确认视频路径、源语言、字幕格式 (SRT/内嵌) |
| 语音转录 | 确认音频/视频路径、输出格式 (文字/SRT) |
| 字幕翻译 | 确认源语言、目标语言、是否烧录 |
| 字幕烧录 | 确认视频路径、字幕文件、输出质量 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行生成 → 返回文件路径

Full docs: read SKILL-REFERENCE.md

Generate movie-style subtitles from video or audio files. Supports transcription, translation, and burning subtitles directly into video.

## Features

- **Chinese (中文)**: FunASR (Alibaba, recommended) or Whisper large-v3
- **English**: OpenAI Whisper large-v3
- **Hebrew**: ivrit.ai fine-tuned model
- **Auto-detect**: Automatically detects language and selects best model
- **Translation**: Translate between zh/en/he
- **Burn-in**: Hardcode subtitles into video (visible everywhere, including WhatsApp)
- **Movie-style**: Natural subtitle breaks (42 chars/line, 1-7s duration)

## Quick Start

```bash
# Plain transcript
./scripts/generate_srt.py video.mp4

# Generate SRT file
./scripts/generate_srt.py video.mp4 --srt

# Burn subtitles into video (always visible)
./scripts/generate_srt.py video.mp4 --srt --burn

# Translate to English + burn in
./scripts/generate_srt.py video.mp4 --srt --burn --translate en

# Force language
./scripts/generate_srt.py video.mp4 --lang zh    # Chinese (default)
./scripts/generate_srt.py video.mp4 --lang en    # English
./scripts/generate_srt.py video.mp4 --lang he    # Hebrew
```

## Options

| Flag | Description |
|------|-------------|
| `--srt` | Generate SRT subtitle file |
| `--burn` | Burn subtitles into video (hardcoded, always visible) |
| `--embed` | Embed soft subtitles (toggle in player) |
| `--translate en` | Translate to English |
| `--lang zh/en/he` | Force input language (default: zh) |
| `-o FILE` | Custom output path |

## Output

- **Default**: Plain text transcript to stdout
- **With `--srt`**: Creates `video.srt` alongside input
- **With `--burn`**: Creates `video_subtitled.mp4` with hardcoded subs

## Requirements

- **uv**: Python package manager (auto-installs dependencies)
- **ffmpeg-full**: For burning subtitles (`brew install ffmpeg-full`)
- **Models**: ~3GB each, auto-downloaded on first use

## Subtitle Style

- Font size 12, white text with black outline
- Bottom-aligned, movie-style positioning
- Max 42 chars/line, 2 lines max
- Natural breaks at punctuation and pauses
