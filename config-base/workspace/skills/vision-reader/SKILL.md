---
name: vision-reader
description: Read and understand image content using vision-capable AI models or OCR. Use when the user asks to read/analyze an image, extract text from a screenshot, understand what's in a photo, do OCR on a document, or needs visual content interpreted. Supports local images and URLs.
triggers: 
metadata: 
openclaw: 
emoji: "👁️"
requires: 
anyBins: ["python3"]
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["vision_reader"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Vision Reader

图片识别助手。**触发后必须先询问用户确认**，再执行分析。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| OCR 提取 | 确认图片路径、识别语言 (中文/英文)、输出格式 |
| 图片分析 | 确认分析深度 (简述/详细)、关注重点 |
| 截图理解 | 确认截图来源、需要提取的信息类型 |
| 文档识别 | 确认文档类型、是否保留格式 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行识别 → 返回结果

Full docs: read SKILL-REFERENCE.md

Analyze images using AI vision models or local OCR.

## Capabilities

1. **AI Vision Analysis** — send image to vision model (qwen3.5-plus, kimi-k2.5) for understanding
2. **OCR Text Extraction** — extract text from images using macOS Vision framework
3. **Screenshot Analysis** — combine with screenshot-sender for screen understanding
4. **Document Reading** — extract text from scanned documents, receipts, etc.

## Method 1: AI Vision Model (Recommended)

Use vision-capable models directly. These models accept image input:

- `bailian/qwen3.5-plus` — 1M context, supports `["text", "image"]`
- `bailian/kimi-k2.5` — 262K context, supports `["text", "image"]`
- `qwen-portal/vision-model` — 128K context, supports `["text", "image"]`

When analyzing images, switch to one of these models if the current model doesn't support image input.

### Workflow

1. User provides image path or URL
2. Agent reads the image file
3. Agent sends to vision model with analysis prompt
4. Return structured analysis

## Method 2: Local OCR (macOS Vision Framework)

For pure text extraction without needing an AI model:

```bash
python3 {baseDir}/scripts/ocr_extract.py <image_path> [--lang zh-Hans,en] [--json]
```

### Parameters

| Flag | Description | Default |
|------|-------------|---------|
| `<image_path>` | Path to image file (PNG, JPG, etc.) | required |
| `--lang` | OCR languages (comma-separated) | `zh-Hans,en` |
| `--json` | Output as JSON with bounding boxes | plain text |
| `--confidence` | Min confidence threshold (0-1) | `0.5` |

### Output (plain text mode)

```
第一行文字
第二行文字
...
```

### Output (JSON mode)

```json
{
  "text": "完整提取文本",
  "blocks": [
    {"text": "第一行", "confidence": 0.98, "bbox": [x, y, w, h]},
    ...
  ],
  "language": "zh-Hans"
}
```

## Method 3: Tesseract OCR (Fallback)

If macOS Vision Framework is unavailable:

```bash
brew install tesseract tesseract-lang
tesseract <image_path> stdout -l chi_sim+eng
```

## Workflow Examples

**User says:** "帮我看看这张图片上写了什么"
1. Get image path
2. Run OCR: `python3 {baseDir}/scripts/ocr_extract.py /path/to/image.png`
3. Return extracted text

**User says:** "分析一下这个截图的内容"
1. Get screenshot path (or take new one with screenshot-sender)
2. Send to vision model (qwen3.5-plus) with prompt: "请详细描述这张截图的内容"
3. Return model analysis

**User says:** "这个价格截图里哪个最便宜？"
1. Run OCR to extract prices
2. Send to vision model for comparison analysis
3. Return structured comparison

## Notes

- macOS Vision Framework requires macOS 10.15+
- For Chinese text, always include `zh-Hans` in language list
- Vision models are more accurate for complex analysis; OCR is faster for pure text
- Large images may be resized before sending to vision models
