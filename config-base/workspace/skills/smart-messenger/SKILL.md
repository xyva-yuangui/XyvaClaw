---
name: smart-messenger
description: Send rich messages to Feishu chats including text, images, cards, and scheduled messages. Use when the user asks to send a message, share an image, create a card/report, schedule a notification, or manage message templates. Integrates with screenshot-sender and vision-reader for multimedia messaging.
triggers: 
metadata: 
openclaw: 
emoji: "💬"
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["smart_messenger"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Smart Messenger

飞书消息助手。**触发后必须先询问用户确认**，再发送消息。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 文本消息 | 确认接收人/群、消息内容、发送时间 |
| 图片消息 | 确认图片来源、接收人、是否添加说明 |
| 卡片报告 | 确认报告类型、数据源、接收人 |
| 定时消息 | 确认发送时间、重复频率、消息内容 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 发送消息 → 记录发送状态

Full docs: read SKILL-REFERENCE.md

Send rich, multi-format messages to Feishu chats with templates and scheduling.

## Capabilities

1. **Text messages** — plain text, markdown-formatted
2. **Image messages** — send local images or screenshots to chats
3. **Interactive cards** — structured cards with titles, content, buttons
4. **Scheduled messages** — time-delayed or cron-based message delivery
5. **Message templates** — reusable templates for recurring reports

## 1. Send Text Message

The agent can send messages directly via Feishu channel tools. For formatted messages:

```bash
# Send via openclaw CLI (if available)
# Or use the feishu plugin's built-in message sending capability

# Template-based sending
python3 {baseDir}/scripts/send_message.py \
  --chat "__GROUP_ID__" \
  --template "daily-report" \
  --vars '{"date": "2026-03-02", "summary": "完成5项任务"}'
```

## 2. Send Image Message

Combine with screenshot-sender:

```bash
# Capture and send screenshot
node ~/.openclaw/workspace/skills/screenshot-sender/scripts/capture-and-send.mjs \
  --chat "__GROUP_ID__" \
  --caption "当前屏幕截图"

# Send existing image
node ~/.openclaw/workspace/skills/screenshot-sender/scripts/capture-and-send.mjs \
  --file /path/to/image.png \
  --chat "__GROUP_ID__"
```

## 3. Interactive Card Format

For sending structured information, use Feishu interactive cards:

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": { "tag": "plain_text", "content": "📊 每日选股报告" },
      "template": "blue"
    },
    "elements": [
      {
        "tag": "markdown",
        "content": "**日期**: 2026-03-02\n**推荐股票**: 10只\n**最高评分**: 85.3"
      },
      {
        "tag": "hr"
      },
      {
        "tag": "markdown",
        "content": "| 排名 | 股票 | 评分 |\n|---|---|---|\n| 1 | 000001 | 85.3 |\n| 2 | 600036 | 82.1 |"
      }
    ]
  }
}
```

## 4. Message Templates

Templates are stored in `{baseDir}/templates/`:

### daily-report.json
```json
{
  "id": "daily-report",
  "name": "每日复盘报告",
  "card": {
    "header": {"title": "📋 每日复盘 - {{date}}"},
    "body": "## 今日完成\n{{completed}}\n\n## 遇到问题\n{{issues}}\n\n## 明日计划\n{{plan}}"
  }
}
```

### stock-alert.json
```json
{
  "id": "stock-alert",
  "name": "选股提醒",
  "card": {
    "header": {"title": "📈 选股推荐 - {{date}}"},
    "body": "**Top {{count}} 候选股**\n\n{{stock_table}}\n\n⚠️ 仅供研究参考，不构成投资建议"
  }
}
```

### morning-briefing.json
```json
{
  "id": "morning-briefing",
  "name": "晨报",
  "card": {
    "header": {"title": "🌅 早安 - {{date}}"},
    "body": "**天气**: {{weather}}\n**待办**: {{todo_count}}项\n**日历**: {{events}}"
  }
}
```

## 5. Template Management

```bash
# List available templates
python3 {baseDir}/scripts/send_message.py --list-templates

# Send with template
python3 {baseDir}/scripts/send_message.py \
  --chat "__GROUP_ID__" \
  --template "daily-report" \
  --vars '{"date": "2026-03-02", "completed": "- 修复截图\n- 清理skills", "issues": "无", "plan": "开发新skill"}'

# Send raw text
python3 {baseDir}/scripts/send_message.py \
  --chat "__GROUP_ID__" \
  --text "这是一条测试消息"
```

## Workflow Examples

**User says:** "帮我发一条消息到群里，告诉大家明天开会"
1. Agent composes message text
2. Send via feishu channel tool to the group chat

**User says:** "把今天的选股结果发到飞书"
1. Load stock screening results
2. Format as interactive card using stock-alert template
3. Send to configured chat

**User says:** "每天早上8点给我发一条晨报"
1. Configure cron job (already in jobs.json)
2. On trigger, gather weather + todo + calendar
3. Format with morning-briefing template
4. Send to chat

## Integration Points

- **screenshot-sender**: Capture + send images
- **vision-reader**: Analyze images before sending descriptions
- **system-control**: Include system status in reports
- **quant-stock-screener**: Format and send screening results
- **cron jobs**: Scheduled message delivery
