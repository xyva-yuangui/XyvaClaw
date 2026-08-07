#!/usr/bin/env python3
"""
calendar_manager.py — 日历管理工具 (macOS)

支持: 查看/添加/删除 macOS 日历事件，提醒，会议创建

用法:
  python3 calendar_manager.py list --days 7
  python3 calendar_manager.py add --title "团队周会" --date "2026-04-01 10:00" --duration 60
  python3 calendar_manager.py add --title "项目截止" --date "2026-04-05" --all-day
  python3 calendar_manager.py today
  python3 calendar_manager.py week
  python3 calendar_manager.py delete --event-id "xxx"
  python3 calendar_manager.py --check
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "calendar"


def _run_applescript(script: str) -> tuple:
    """执行 AppleScript，返回 (stdout, returncode)"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.returncode


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _parse_datetime(dt_str: str) -> datetime:
    """解析多种日期格式"""
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%m-%d %H:%M",
        "%m/%d %H:%M",
    ]
    now = datetime.now()
    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt
        except ValueError:
            continue
    raise ValueError(f"无法解析日期格式: {dt_str}")


def cmd_add(title: str, date_str: str, duration: int = 60,
            location: str = "", notes: str = "", all_day: bool = False,
            calendar_name: str = "Calendar", remind_min: int = 15) -> dict:
    if not _is_macos():
        return {"status": "fail", "message": "calendar-manager 仅支持 macOS"}

    dt = _parse_datetime(date_str)
    end_dt = dt + timedelta(minutes=duration)

    dt_apple = dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    end_apple = end_dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")

    if all_day:
        script = f"""
tell application "Calendar"
    tell calendar "{calendar_name}"
        set newEvent to make new event with properties {{summary:"{title}", start date:date "{dt_apple}", end date:date "{end_apple}", allday event:true}}
        set location of newEvent to "{location}"
        set description of newEvent to "{notes}"
    end tell
    save
end tell
return "ok"
"""
    else:
        script = f"""
tell application "Calendar"
    tell calendar "{calendar_name}"
        set startDate to date "{dt_apple}"
        set endDate to date "{end_apple}"
        set newEvent to make new event with properties {{summary:"{title}", start date:startDate, end date:endDate}}
        set location of newEvent to "{location}"
        set description of newEvent to "{notes}"
    end tell
    save
end tell
return "ok"
"""

    output, rc = _run_applescript(script)
    if rc == 0:
        return {
            "status": "ok",
            "title": title,
            "date": dt.strftime("%Y-%m-%d %H:%M"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
            "duration": duration,
            "all_day": all_day,
            "calendar": calendar_name,
        }
    return {"status": "fail", "message": f"AppleScript 错误: {output}"}


def cmd_list(days: int = 7, calendar_name: str = "") -> dict:
    if not _is_macos():
        return {"status": "fail", "message": "calendar-manager 仅支持 macOS"}

    start = datetime.now()
    end = start + timedelta(days=days)

    start_str = start.strftime("%A, %B %d, %Y at %I:%M:%S %p")
    end_str = end.strftime("%A, %B %d, %Y at %I:%M:%S %p")

    cal_filter = f'whose name is "{calendar_name}"' if calendar_name else ""

    script = f"""
set startDate to date "{start_str}"
set endDate to date "{end_str}"
set eventList to {{}}
tell application "Calendar"
    set allCals to every calendar {cal_filter}
    repeat with aCal in allCals
        set calEvents to (every event of aCal whose start date >= startDate and start date <= endDate)
        repeat with anEvent in calEvents
            set eventInfo to (summary of anEvent) & "|" & (start date of anEvent as string) & "|" & (end date of anEvent as string)
            set end of eventList to eventInfo
        end repeat
    end repeat
end tell
set AppleScript's text item delimiters to "\\n"
return eventList as string
"""

    output, rc = _run_applescript(script)
    if rc != 0:
        return {"status": "fail", "message": f"获取日历失败: {output}"}

    events = []
    for line in output.split('\n'):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                events.append({
                    "title": parts[0],
                    "start": parts[1] if len(parts) > 1 else "",
                    "end": parts[2] if len(parts) > 2 else "",
                })

    events.sort(key=lambda x: x.get("start", ""))
    return {"status": "ok", "days": days, "count": len(events), "events": events}


def cmd_today() -> dict:
    return cmd_list(days=1)


def cmd_week() -> dict:
    return cmd_list(days=7)


def cmd_open():
    """打开系统日历应用"""
    if _is_macos():
        subprocess.run(["open", "-a", "Calendar"])
        return {"status": "ok", "message": "已打开日历应用"}
    return {"status": "fail", "message": "仅支持 macOS"}


def health_check() -> dict:
    checks = []
    if _is_macos():
        checks.append({"name": "macOS", "status": "ok", "message": "系统兼容"})
        _, rc = _run_applescript('tell application "Calendar" to return name of first calendar')
        checks.append({"name": "日历访问权限", "status": "ok" if rc == 0 else "warn",
                       "message": "已授权" if rc == 0 else "需要在系统偏好设置中授权日历访问"})
    else:
        checks.append({"name": "macOS", "status": "fail",
                       "message": f"当前系统 {sys.platform} 不支持，需要 macOS"})
    overall = "fail" if any(c["status"] == "fail" for c in checks) else "ok"
    return {"skill": "calendar-manager", "version": "1.0.0", "status": overall, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="macOS 日历管理工具")
    parser.add_argument("command", nargs="?",
                        choices=["add", "list", "today", "week", "delete", "open"])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--title", default="")
    parser.add_argument("--date", default="")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--location", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--all-day", action="store_true")
    parser.add_argument("--calendar", default="Calendar")
    parser.add_argument("--remind", type=int, default=15, help="提前提醒分钟数")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--event-id", default="")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    if args.check:
        result = health_check()
    elif args.command == "add":
        if not args.title or not args.date:
            print("错误: --title 和 --date 必填", file=sys.stderr); sys.exit(1)
        result = cmd_add(args.title, args.date, args.duration, args.location,
                         args.notes, args.all_day, args.calendar, args.remind)
    elif args.command == "list":
        result = cmd_list(args.days, args.calendar if args.calendar != "Calendar" else "")
    elif args.command == "today":
        result = cmd_today()
    elif args.command == "week":
        result = cmd_week()
    elif args.command == "open":
        result = cmd_open()
    else:
        parser.print_help(); sys.exit(0)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result.get("status")
        if s == "ok":
            if "events" in result:
                print(f"📅 未来 {result['days']} 天，共 {result['count']} 个事件:")
                for e in result["events"][:20]:
                    print(f"  • {e.get('start','')[:16]} | {e.get('title','')}")
            elif "title" in result and "date" in result:
                print(f"✅ 已添加事件: {result['title']}")
                print(f"   时间: {result['date']} → {result['end']}")
            elif "checks" in result:
                for c in result["checks"]:
                    icon = "✅" if c["status"] == "ok" else ("⚠️" if c["status"] == "warn" else "❌")
                    print(f"  {icon} {c['name']}: {c['message']}")
            else:
                print(f"✅ {result.get('message','完成')}")
        else:
            print(f"❌ {result.get('message','失败')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
