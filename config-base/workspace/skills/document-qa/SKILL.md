---
name: document-qa
description: 文档问答工具。对 PDF/Word/TXT/MD/CSV 文件进行自然语言问答，自动提取内容、检索相关段落并用 LLM 给出精准回答。支持单文件和整个目录。
version: 1.0.0
status: stable
updated: 2026-03-31
category: documents
---

# Document QA — 文档问答

**触发场景**: 快速从合同/报告/文档中找答案，问"这份合同违约金多少"、"Q3销售目标是什么"。

## 用法

```bash
# 问单个文件
python3 {baseDir}/scripts/doc_qa.py ask --file contract.pdf "违约金条款是什么？"

# 问整个目录（会搜索所有文档）
python3 {baseDir}/scripts/doc_qa.py ask --dir ./docs "公司的退货政策是什么？"

# 扩大检索块数
python3 {baseDir}/scripts/doc_qa.py ask --file report.pdf --top-k 8 "Q3 销售目标完成情况"

# 健康检查
python3 {baseDir}/scripts/doc_qa.py --check
```

## 支持格式

`.pdf` `.docx` `.doc` `.txt` `.md` `.csv` `.xlsx`

## 注意

- 首次使用大文档（>50页）需要约 10-60 秒提取时间
- 问答历史自动保存至 `~/.openclaw/output/doc_qa/qa_history.jsonl`
