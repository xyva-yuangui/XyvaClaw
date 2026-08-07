---
name: document-suite
description: 文档处理全能套件。统一处理 PDF/Word/Excel/PPT/Markdown 的读取、生成、转换和问答。消除用户在多个文档skill间的选择困难。
version: 1.0.0
status: stable
updated: 2026-04-01
category: document
provides: ["pdf_read", "pdf_generate", "word_generate", "excel_operation", "ppt_generate", "document_qa", "markdown_convert"]
os: ["darwin", "linux"]
triggers:
metadata:
  openclaw:
    emoji: "📄"
    category: document
    priority: 75
---

# Document Suite — 文档处理全能套件

统一文档处理入口，按文件类型和操作意图自动路由到对应子模块。

## 子模块路由

| 意图 | 子模块 | 原 Skill |
|------|--------|----------|
| pdf_read / pdf 解析 | `pdf-reader` | pdf-reader |
| pdf_generate / 导出PDF | `pdf-generator` | pdf-generator |
| excel_operation | `excel-xlsx` | excel-xlsx |
| word_generation | `word-docx-1.0.0` | word-docx-1.0.0 |
| ppt_generate / ppt_create | `ppt-agent` + `pptx-reader-writer` | ppt-agent, pptx-reader-writer |
| document_qa | `document-qa` | document-qa |
| markdown_convert | `markdown-converter` | markdown-converter |

## 路由逻辑

1. 用户消息中包含文件类型关键词（pdf/word/excel/ppt）→ 直接路由
2. 用户上传文件 → 根据文件扩展名路由
3. "帮我看看这个文件" → 先检测文件类型，再路由
4. 文档问答（从文件中提取/查找/总结）→ document-qa

## 子模块保持独立

所有子模块保留原有目录结构和独立调用能力。document-suite 仅作为统一调度层。
