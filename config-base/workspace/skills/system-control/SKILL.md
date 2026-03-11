---
name: system-control
description: Control and monitor macOS system functions. Use when the user asks about system info (CPU, memory, disk, battery), app management (launch/quit apps, window list), notifications, clipboard operations, volume/brightness control, or any OS-level task on macOS.
triggers: 
metadata: 
openclaw: 
emoji: "🖥️"
requires: 
anyBins: ["osascript"]
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["system-control", "os-management"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🖥️", "category": "tools", "priority": "medium"}
---

# System Control (macOS)

macOS 系统控制助手。**触发后必须先询问用户确认**，再执行操作。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 系统查询 | 确认查询类型 (CPU/内存/磁盘/电池) |
| 应用管理 | 确认操作类型 (打开/关闭/切换)、目标应用 |
| 通知发送 | 确认通知内容、标题、声音 |
| 音量调节 | ⚠️ 确认当前音量、目标音量、是否静音 |
| 进程管理 | ⚠️ 确认进程名称、操作类型 (查看/终止) |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行操作 → 返回结果

**安全规则**: 强制退出应用前必须确认 | 音量>80 需警告 | 优先使用 trash 删除

Full docs: read SKILL-REFERENCE.md

Monitor and control macOS system functions via native commands and AppleScript.

## 1. System Information

```bash
# Hardware overview
system_profiler SPHardwareDataType 2>/dev/null | grep -E "Model|Chip|Memory|Serial"

# CPU & memory usage (snapshot)
top -l 1 -s 0 | head -12

# Disk usage
df -h / | tail -1

# Battery status (laptops)
pmset -g batt

# Network info
ifconfig en0 | grep "inet " && networksetup -getairportnetwork en0 2>/dev/null

# Uptime
uptime

# macOS version
sw_vers
```

### Bundled script for quick system report

```bash
python3 {baseDir}/scripts/sysinfo.py [--json]
```

Returns: CPU%, memory%, disk%, battery%, network status, uptime.

## 2. Application Management

```bash
# List running visible apps
osascript -e 'tell application "System Events" to get name of every process whose visible is true'

# Launch an app
open -a "Safari"
open -a "Visual Studio Code"

# Quit an app (graceful)
osascript -e 'tell application "Safari" to quit'

# Force-quit an app
kill -9 $(pgrep -x "AppName")

# Get frontmost app
osascript -e 'tell application "System Events" to get name of first process whose frontmost is true'

# List all windows of an app
osascript -e 'tell application "System Events" to tell process "Safari" to get name of every window'

# Bring app to front
osascript -e 'tell application "Safari" to activate'
```

## 3. Notifications

```bash
# Send a macOS notification
osascript -e 'display notification "消息内容" with title "标题" subtitle "副标题" sound name "default"'

# Notification with custom sound
osascript -e 'display notification "提醒" with title "老贾提醒" sound name "Glass"'
```

## 4. Clipboard

```bash
# Read clipboard content
pbpaste

# Write to clipboard
echo "要复制的内容" | pbcopy

# Copy file content to clipboard
pbcopy < /path/to/file.txt
```

## 5. Volume & Display

```bash
# Get current volume (0-100)
osascript -e 'output volume of (get volume settings)'

# Set volume (0-100)
osascript -e 'set volume output volume 50'

# Mute/unmute
osascript -e 'set volume output muted true'
osascript -e 'set volume output muted false'

# Get brightness (requires brightness CLI or AppleScript)
# Install: brew install brightness
brightness -l 2>/dev/null || echo "brightness CLI not installed"
```

## 6. File Management Shortcuts

```bash
# Open file in default app
open /path/to/file.pdf

# Open folder in Finder
open /path/to/folder

# Reveal file in Finder
open -R /path/to/file.txt

# Move to Trash (safe delete)
trash /path/to/file  # requires: brew install trash
# Or use Finder:
osascript -e 'tell application "Finder" to delete POSIX file "/path/to/file"'

# Quick Look preview
qlmanage -p /path/to/file.png 2>/dev/null
```

## 7. Process Management

```bash
# Find process by name
pgrep -fl "process_name"

# Kill process
kill <pid>
kill -9 <pid>  # force

# List top CPU consumers
ps aux --sort=-%cpu | head -10

# List top memory consumers
ps aux --sort=-%mem | head -10
```

## 8. Network

```bash
# Current WiFi network
networksetup -getairportnetwork en0 2>/dev/null

# Public IP
curl -s ifconfig.me

# Local IP
ipconfig getifaddr en0

# DNS lookup
nslookup example.com

# Ping test
ping -c 3 8.8.8.8

# Port check
nc -z -w 3 host port
```

## Safety Rules

- **Never force-quit without asking** — data loss risk
- **Never change system settings** (firewall, sharing, users) without explicit permission
- **Prefer `trash` over `rm`** — recoverable deletion
- **Volume changes**: warn user before setting volume > 80
- **App launches**: safe to do freely; app quits need confirmation
