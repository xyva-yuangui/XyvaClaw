---
name: translation
description: 专业翻译工具。用户需要翻译文本、文件、电商 Listing、合同、物流文件时使用。支持中英日韩等14种语言互译，内置电商/法律/物流专业词汇表，确保术语准确。
version: 1.0.0
status: stable
updated: 2026-03-31
category: content
provides: ["translation", "multilingual"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🌐", "category": "content", "priority": "medium"}
---

# Translation — 专业翻译

**触发场景**: 用户需要翻译文字、文档、商品描述、合同、物流单据。

## 支持语言

`zh` 中文 / `en` 英文 / `ja` 日文 / `ko` 韩文 / `fr` 法文 / `de` 德文 / `es` 西班牙文 / `th` 泰文 / `vi` 越南文 / `id` 印尼文

## 翻译领域（专业词汇表）

| 领域 | 标识符 | 词汇表覆盖 |
|------|--------|---------|
| 电商 | `ecommerce` | 爆款/大促/SKU/退货/包邮等 |
| 法律 | `legal` | 甲乙方/违约金/不可抗力/仲裁等 |
| 物流 | `logistics` | 清关/FOB/CIF/提单/HS编码等 |
| 通用 | `general` | 无专业词汇表 |

## 用法

```bash
# 文本翻译
python3 {baseDir}/scripts/translate.py text "2026最值得买的降噪耳机" --to en

# 带领域词汇表
python3 {baseDir}/scripts/translate.py text "本合同甲方违约须支付违约金" --to en --domain legal

# 文件翻译（支持 .txt/.md/.pdf/.docx）
python3 {baseDir}/scripts/translate.py file contract.pdf --to en --domain legal

# CSV 批量翻译（指定列名）
python3 {baseDir}/scripts/translate.py batch products.csv \
  --col description --to en --domain ecommerce

# 电商 Listing 翻译（自动适配平台字数限制）
python3 {baseDir}/scripts/translate.py ecommerce \
  --input listing_zh.json \
  --platform amazon \
  --to en

# 健康检查
python3 {baseDir}/scripts/translate.py --check
```

## 输出

- 文本翻译: 直接打印到终端
- 文件/批量/电商: 保存至 `~/.openclaw/output/translations/`
