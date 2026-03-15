---
name: pdf-processor
description: PDF 文档处理。支持提取文本、提取表格、合并 PDF、拆分 PDF、PDF 转图片、获取元数据。用户需要处理 PDF 文件时使用此技能。
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-15
provides: ["pdf_processor"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "📄", "category": "tools", "priority": "medium"}
---

# PDF Processor

PDF 文档处理工具。

## 功能

- **提取文本** — 从 PDF 中提取全部或指定页的纯文本
- **提取表格** — 从 PDF 中提取表格为 CSV/JSON
- **合并 PDF** — 将多个 PDF 合并为一个
- **拆分 PDF** — 将 PDF 按页码范围拆分
- **元数据** — 读取 PDF 标题、作者、页数等信息
- **PDF 转图片** — 将 PDF 每页转为 PNG（需要 pdf2image + poppler）

## 使用方式

```bash
# 健康检查
python3 scripts/check.py

# 提取文本
python3 scripts/pdf_tool.py extract-text --input doc.pdf
python3 scripts/pdf_tool.py extract-text --input doc.pdf --pages 1-5

# 提取表格
python3 scripts/pdf_tool.py extract-tables --input doc.pdf --format csv

# 合并 PDF
python3 scripts/pdf_tool.py merge --inputs a.pdf b.pdf c.pdf --output merged.pdf

# 拆分 PDF
python3 scripts/pdf_tool.py split --input doc.pdf --pages 1-3 --output part1.pdf

# 元数据
python3 scripts/pdf_tool.py info --input doc.pdf

# 转图片
python3 scripts/pdf_tool.py to-images --input doc.pdf --output-dir ./images/
```

## 输出目录

`$OPENCLAW_HOME/workspace/output/pdf/`

## 依赖

- pdfplumber (`pip3 install pdfplumber`)
- PyPDF2 (`pip3 install PyPDF2`)
