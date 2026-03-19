---
name: screenshot-sender
description: Capture screenshots on macOS and optionally send them to Feishu chats. Use when the user asks to take a screenshot, capture the screen, send a screenshot, or needs visual evidence of something on screen. Supports full screen, window, and region capture modes.
triggers: 
metadata: 
openclaw: 
emoji: "📸"
requires: 
anyBins: ["screencapture"]
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["screenshot_sender"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Screenshot Sender

Capture macOS screenshots and send them to Feishu chats.

## Capabilities

1. **Full screen capture** — capture the entire screen
2. **Window capture** — capture a specific window (interactive selection)
3. **Region capture** — capture a selected screen region
4. **Auto-send to Feishu** — upload and send captured image to a chat
5. **Silent mode** — no shutter sound

## Usage

### Capture screenshot (save to file)

```bash
# Full screen (silent, no shadow)
/usr/sbin/screencapture -x -o /tmp/screenshot_$(date +%s).png

# Interactive window selection
/usr/sbin/screencapture -x -w /tmp/screenshot_$(date +%s).png

# Interactive region selection
/usr/sbin/screencapture -x -s /tmp/screenshot_$(date +%s).png

# Capture to clipboard instead of file
/usr/sbin/screencapture -x -c
```

### Capture and send to Feishu

Use the bundled script to capture + upload + send in one step:

```bash
# Capture full screen and send to default chat
node {baseDir}/scripts/capture-and-send.mjs

# Capture and send to specific chat
node {baseDir}/scripts/capture-and-send.mjs --chat "__GROUP_ID__"

# Send an existing image file
node {baseDir}/scripts/capture-and-send.mjs --file /path/to/image.png

# Capture with a message caption
node {baseDir}/scripts/capture-and-send.mjs --caption "这是当前屏幕截图"
```

### Parameters

| Flag | Description | Default |
|------|-------------|---------|
| `--mode` | Capture mode: `full`, `window`, `region` | `full` |
| `--chat` | Feishu chat ID to send to | default group |
| `--file` | Send existing file instead of capturing | — |
| `--caption` | Text message to send with the image | — |
| `--output` | Save path (also keeps local copy when sending) | `/tmp/screenshot_<ts>.png` |
| `--no-send` | Only capture, don't send to Feishu | `false` |

## macOS Permissions

First-time use requires **Screen Recording** permission:
- System Settings → Privacy & Security → Screen Recording → enable for Terminal / openclaw process

## Workflow Examples

**User says:** "帮我截图当前屏幕发过来"
1. Run: `/usr/sbin/screencapture -x -o /tmp/screenshot_$(date +%s).png`
2. Upload image to Feishu via media API
3. Send image message to chat

**User says:** "截一下这个窗口"
1. Run: `/usr/sbin/screencapture -x -w /tmp/screenshot_$(date +%s).png`
2. Upload + send

## Notes

- Screenshots are saved as PNG format
- `-x` flag suppresses the shutter sound
- `-o` flag removes window shadows
- Files in `/tmp/` are auto-cleaned on reboot
- For privacy, always tell the user before taking a screenshot
