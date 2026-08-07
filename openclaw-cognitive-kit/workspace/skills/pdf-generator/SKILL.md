---
name: pdf-generator
description: PDF生成器。从Markdown、HTML或模板数据生成专业排版的PDF文档。
triggers: 
metadata: 
openclaw: 
emoji: "📄"
requires: 
bins: ["uv"]
version: 1.0.0
status: stable
updated: 2026-03-21
provides: ["pdf-generation"]
os: ["darwin", "linux"]
clawdbot: {"emoji": "📄", "category": "tools", "priority": "medium"}
---

# PDF Generator

从Markdown/HTML/文本生成专业排版PDF。**触发后先确认内容和格式。**

## Usage

```bash
# 从Markdown文件生成
uv run {baseDir}/scripts/generate_pdf.py --input report.md --output report.pdf

# 从文本直接生成
uv run {baseDir}/scripts/generate_pdf.py --text "报告内容..." --output report.pdf --title "标题"

# 使用报告模板
uv run {baseDir}/scripts/generate_pdf.py --template report --data '{"title":"月度分析","sections":[{"title":"概述","content":"<p>...</p>"}]}' --output report.pdf

# 列出模板
uv run {baseDir}/scripts/generate_pdf.py --list-templates
```

## 内置模板

| 模板 | 用途 |
|------|------|
| report | 分析报告(封面+摘要+指标+分节) |

## 依赖

macOS: `brew install pango` + `pip3 install weasyprint jinja2 markdown`

## Workflow

1. 执行 generate_pdf.py
2. 解析输出中 `MEDIA:` 行获取文件路径
3. 向用户展示生成结果

## Notes

- 支持中文排版(PingFang SC / Noto Sans CJK)
- A4页面，自动分页，页码
- 模板使用Jinja2语法
