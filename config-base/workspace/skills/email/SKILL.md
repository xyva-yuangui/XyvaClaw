---
name: email
description: 邮件收发。支持通过 IMAP 读取邮件、SMTP 发送邮件、搜索邮件、下载附件。用户需要处理邮件时使用此技能。
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-15
provides: ["email"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "📧", "category": "tools", "priority": "medium"}
---

# Email — 邮件收发

通过 IMAP/SMTP 协议收发邮件。

## 功能

- **读取邮件** — 获取收件箱最新邮件（标题、发件人、正文、附件）
- **搜索邮件** — 按发件人、主题、日期范围搜索
- **发送邮件** — 发送纯文本或 HTML 邮件，支持附件
- **回复邮件** — 回复指定邮件
- **下载附件** — 保存邮件附件到本地

## 使用方式

```bash
# 健康检查
python3 scripts/check.py

# 读取最新 10 封邮件
python3 scripts/email_tool.py inbox --limit 10

# 搜索邮件
python3 scripts/email_tool.py search --from "boss@company.com" --days 7

# 读取指定邮件详情
python3 scripts/email_tool.py read --id 12345

# 发送邮件
python3 scripts/email_tool.py send --to "user@example.com" --subject "标题" --body "内容"

# 发送带附件的邮件
python3 scripts/email_tool.py send --to "user@example.com" --subject "报告" --body "见附件" --attach report.pdf

# 下载附件
python3 scripts/email_tool.py download-attachments --id 12345 --output-dir ./attachments/
```

## 配置

在 `$OPENCLAW_HOME/.env` 中添加：

```bash
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USER=your@email.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=your@email.com
```

常见邮箱配置：
- **Gmail**: IMAP imap.gmail.com:993, SMTP smtp.gmail.com:587（需开启应用专用密码）
- **QQ邮箱**: IMAP imap.qq.com:993, SMTP smtp.qq.com:587（需开启 IMAP 并获取授权码）
- **163邮箱**: IMAP imap.163.com:993, SMTP smtp.163.com:465
- **Outlook**: IMAP outlook.office365.com:993, SMTP smtp.office365.com:587

## 输出目录

`$OPENCLAW_HOME/workspace/output/email/`

## 依赖

Python 标准库（imaplib, smtplib, email），无需额外安装。
