---
name: qwen-image
description: Generate images using Qwen Image API (Alibaba Cloud DashScope). Use when users request image generation with Chinese prompts or need high-quality AI-generated images from text descriptions.
triggers: 
metadata: 
openclaw: 
emoji: "🎨"
requires: 
bins: ["uv"]
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["image-generation", "ai-art"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🖼️", "category": "tools", "priority": "medium"}
---

# Qwen Image

AI 图片生成助手。**触发后必须先询问用户确认**，再执行生成。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 图片生成 | 确认画面描述、尺寸比例 (16:9/1:1/9:16)、风格 |
| 封面设计 | 确认主题文字、配色风格、用途场景 |
| 海报创作 | 确认海报内容、文字元素、目标受众 |
| 艺术创作 | 确认艺术风格、参考图片 (可选)、情绪基调 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行生成 → 返回图片 URL

**注意**: 默认返回 URL 不下载，如需保存需用户确认

Full docs: read SKILL-REFERENCE.md

Generate high-quality images using Alibaba Cloud's Qwen Image API (通义万相).

## Usage

### 快速开始

Generate an image (returns URL only):
```bash
# 使用默认模型（qwen-image-max）
uv run {baseDir}/scripts/generate_image.py --prompt "一副典雅庄重的对联悬挂于厅堂之中" --size "1664*928"
```

Generate and save locally:
```bash
# 保存为本地文件
uv run {baseDir}/scripts/generate_image.py --prompt "一副典雅庄重的对联悬挂于厅堂之中" --filename output.png
```

### 选择模型

```bash
# 千问旗舰版（适合复杂文字渲染）
uv run {baseDir}/scripts/generate_image.py --prompt "海报设计，含文字" --model qwen-image-max

# 万相性价比之王（适合快速测试）⭐ 推荐
uv run {baseDir}/scripts/generate_image.py --prompt "时尚人像摄影" --model wanx2.2-t2i-flash

# 万相专业版（适合电商主图）⭐ 推荐
uv run {baseDir}/scripts/generate_image.py --prompt "电商产品主图，白色背景" --model wanx2.1-pro
```

## 支持的模型

### 万相 2.6 系列（同步调用，推荐）⭐
- `wan2.6-t2i` - **最新版**，支持自定义分辨率，推荐默认使用

### 万相 2.5 及以下（异步调用）
- `wan2.5-t2i-preview` - 预览版，支持自由尺寸
- `wan2.2-t2i-flash` - **性价比之王** ¥0.05/张，速度最快
- `wan2.2-t2i-plus` - 专业版，稳定性更好
- `wanx2.1-t2i-turbo` - 2.1 极速版
- `wanx2.1-t2i-plus` - 2.1 专业版

```bash
# 使用千问（适合文字渲染）
uv run {baseDir}/scripts/generate_image.py --prompt "一副典雅庄重的对联" --model qwen-image-plus-2026-01-09

# 使用万相（适合写实摄影）⭐
uv run {baseDir}/scripts/generate_image.py --prompt "时尚摄影风格的街拍人像" --model wanx2.2-t2i-flash
uv run {baseDir}/scripts/generate_image.py --prompt "电商产品主图" --model wanx2.1-pro
```

## API Key
You can obtain the API key and run the image generation command in the following order.

- Get apiKey from `models.providers.bailian.apiKey` in `~/.openclaw/openclaw.json`
- Or get from `skills."qwen-image".apiKey` in `~/.openclaw/openclaw.json`
- Or get from `DASHSCOPE_API_KEY` environment variable
- Or Get your API key from: https://dashscope.console.aliyun.com/

## Options
**Sizes:**
- `1664*928` (default) - 16:9 landscape
- `1024*1024` - Square format
- `720*1280` - 9:16 portrait
- `1280*720` - 16:9 landscape (smaller)

**Additional flags:**
- `--negative-prompt "unwanted elements"` - Specify what to avoid
- `--no-prompt-extend` - Disable automatic prompt enhancement
- `--watermark` - Add watermark to generated image
- `--no-verify-ssl` - Disable SSL certificate verification (use when behind corporate proxy)

## Workflow

1. Execute the generate_image.py script with the user's prompt
2. Parse the script output and find the line starting with `MEDIA_URL:`
3. Extract the image URL from that line (format: `MEDIA_URL: https://...`)
4. Display the image to the user using markdown syntax: `![Generated Image](URL)`
5. Do NOT download or save the image unless the user specifically requests it

## Notes

- Supports both Chinese and English prompts
- By default, returns image URL directly without downloading
- The script prints `MEDIA_URL:` in the output - extract this URL and display it using markdown image syntax: `![generated image](URL)`
- Always look for the line starting with `MEDIA_URL:` in the script output and render the image for the user
- Default negative prompt helps avoid common AI artifacts
- Images are hosted on Alibaba Cloud OSS with temporary access URLs
