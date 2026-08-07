---
name: calendar-manager
description: macOS 日历管理工具。通过 AppleScript 操作系统日历，添加/查看/删除事件，查看今日和本周安排，无需第三方依赖。
version: 1.0.0
status: stable
updated: 2026-03-31
category: productivity
os: ["darwin"]
---

# Calendar Manager — 日历管理

**触发场景**: 添加日历事件、查看今天/本周安排、创建会议/截止日期提醒。

## 用法

```bash
# 添加会议
python3 {baseDir}/scripts/calendar_manager.py add \
  --title "Q2 销售复盘" \
  --date "2026-04-01 10:00" \
  --duration 60 \
  --location "会议室A" \
  --notes "请提前准备Q1数据"

# 添加全天事件
python3 {baseDir}/scripts/calendar_manager.py add \
  --title "项目交付截止" \
  --date "2026-04-05" \
  --all-day

# 查看今天安排
python3 {baseDir}/scripts/calendar_manager.py today

# 查看本周安排
python3 {baseDir}/scripts/calendar_manager.py week

# 查看未来 14 天
python3 {baseDir}/scripts/calendar_manager.py list --days 14

# 打开日历应用
python3 {baseDir}/scripts/calendar_manager.py open
```

## 注意

- **仅支持 macOS**，使用 AppleScript 调用系统日历
- 首次使用需在「系统偏好设置 → 安全性与隐私 → 日历」中授权
