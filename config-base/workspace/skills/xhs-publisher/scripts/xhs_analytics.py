#!/usr/bin/env python3
"""
Xiaohongshu Analytics - 发布后数据追踪
功能：获取已发布笔记的数据（阅读、点赞、收藏、评论等），存储到 effect-tracker
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

SKILLS_DIR = Path.home() / ".openclaw" / "workspace" / "skills"
OUTPUT_BASE = Path.home() / ".openclaw" / "output" / "xhs-analytics"
CDP_SCRIPT = SKILLS_DIR / "xiaohongshu-cdp" / "scripts" / "cdp_publish.py"
TRACKER_SCRIPT = SKILLS_DIR / "effect-tracker" / "scripts" / "tracker.py"
PUBLISH_LOG = Path.home() / ".openclaw" / "output" / "xhs-publisher" / "publish_log.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fetch_content_data() -> list:
    """从 CDP 获取内容数据"""
    print("📊 获取发布数据...")
    
    result = subprocess.run(
        [sys.executable, str(CDP_SCRIPT), "content-data", "--page-size", "50"],
        capture_output=True, text=True, timeout=60
    )
    
    # 解析输出中的 JSON
    output = result.stdout
    json_start = output.find("CONTENT_DATA_RESULT:")
    if json_start == -1:
        print(f"❌ 未找到数据：{output[:200]}")
        return []
    
    json_str = output[json_start + len("CONTENT_DATA_RESULT:"):].strip()
    try:
        data = json.loads(json_str)
        rows = data.get("rows", [])
        print(f"✅ 获取到 {len(rows)} 条笔记数据")
        return rows
    except Exception as e:
        print(f"❌ 解析 JSON 失败：{e}")
        return []


def calculate_engagement_rate(row: dict) -> float:
    """计算互动率"""
    view = row.get("观看", 0) or 0
    like = row.get("点赞", 0) or 0
    collect = row.get("收藏", 0) or 0
    comment = row.get("评论", 0) or 0
    
    if view == 0:
        return 0.0
    
    engagement = (like + collect + comment) / view * 100
    return round(engagement, 2)


def analyze_performance(rows: list) -> dict:
    """分析笔记表现"""
    if not rows:
        return {}
    
    total_notes = len(rows)
    total_views = sum(r.get("观看", 0) or 0 for r in rows)
    total_likes = sum(r.get("点赞", 0) or 0 for r in rows)
    total_collects = sum(r.get("收藏", 0) or 0 for r in rows)
    total_comments = sum(r.get("评论", 0) or 0 for r in rows)
    
    # 找出表现最好的笔记
    best_by_view = max(rows, key=lambda r: r.get("观看", 0) or 0) if rows else {}
    best_by_like = max(rows, key=lambda r: r.get("点赞", 0) or 0) if rows else {}
    best_by_collect = max(rows, key=lambda r: r.get("收藏", 0) or 0) if rows else {}
    
    # 计算平均互动率
    engagement_rates = [calculate_engagement_rate(r) for r in rows]
    avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0
    
    return {
        "total_notes": total_notes,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_collects": total_collects,
        "total_comments": total_comments,
        "avg_engagement_rate": round(avg_engagement, 2),
        "best_by_view": {
            "title": best_by_view.get("标题", ""),
            "views": best_by_view.get("观看", 0),
            "engagement": calculate_engagement_rate(best_by_view)
        },
        "best_by_like": {
            "title": best_by_like.get("标题", ""),
            "likes": best_by_like.get("点赞", 0),
            "views": best_by_like.get("观看", 0)
        },
        "best_by_collect": {
            "title": best_by_collect.get("标题", ""),
            "collects": best_by_collect.get("收藏", 0),
            "views": best_by_collect.get("观看", 0)
        }
    }


def record_to_tracker(rows: list):
    """将数据记录到 effect-tracker"""
    print("📝 记录到效果追踪...")
    
    for row in rows:
        title = row.get("标题", "未知")
        views = row.get("观看", 0) or 0
        likes = row.get("点赞", 0) or 0
        collects = row.get("收藏", 0) or 0
        comments = row.get("评论", 0) or 0
        
        # 记录到 tracker
        subprocess.run(
            [sys.executable, str(TRACKER_SCRIPT), "record",
             "--skill", "xhs-publisher", "--action", "published", "--status", "ok",
             "--metadata", json.dumps({
                 "title": title,
                 "views": views,
                 "likes": likes,
                 "collects": collects,
                 "comments": comments,
                 "engagement_rate": calculate_engagement_rate(row)
             }, ensure_ascii=False)],
            capture_output=True, timeout=5
        )
    
    print(f"✅ 已记录 {len(rows)} 条数据到 effect-tracker")


def save_report(analysis: dict, rows: list):
    """保存分析报告"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_BASE / f"report_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存详细数据
    with open(out_dir / "raw_data.json", "w", encoding="utf-8") as f:
        json.dump({"rows": rows, "analysis": analysis}, f, indent=2, ensure_ascii=False)
    
    # 生成 Markdown 报告
    md_content = f"""# 小红书发布数据报告

**生成时间**: {_now()}

---

## 📊 总体数据

| 指标 | 数值 |
|------|------|
| 总笔记数 | {analysis.get('total_notes', 0)} |
| 总曝光 | {analysis.get('total_views', 0)} |
| 总点赞 | {analysis.get('total_likes', 0)} |
| 总收藏 | {analysis.get('total_collects', 0)} |
| 总评论 | {analysis.get('total_comments', 0)} |
| 平均互动率 | {analysis.get('avg_engagement_rate', 0)}% |

---

## 🏆 最佳表现

### 最高观看
- **标题**: {analysis.get('best_by_view', {}).get('title', 'N/A')}
- **观看**: {analysis.get('best_by_view', {}).get('views', 0)}
- **互动率**: {analysis.get('best_by_view', {}).get('engagement', 0)}%

### 最高点赞
- **标题**: {analysis.get('best_by_like', {}).get('title', 'N/A')}
- **点赞**: {analysis.get('best_by_like', {}).get('likes', 0)}
- **观看**: {analysis.get('best_by_like', {}).get('views', 0)}

### 最高收藏
- **标题**: {analysis.get('best_by_collect', {}).get('title', 'N/A')}
- **收藏**: {analysis.get('best_by_collect', {}).get('collects', 0)}
- **观看**: {analysis.get('best_by_collect', {}).get('views', 0)}

---

## 📈 详细数据

| 标题 | 观看 | 点赞 | 收藏 | 评论 | 互动率 |
|------|------|------|------|------|--------|
"""
    
    for row in rows[:20]:  # 只显示前 20 条
        title = row.get("标题", "未知")[:30]
        views = row.get("观看", 0) or 0
        likes = row.get("点赞", 0) or 0
        collects = row.get("收藏", 0) or 0
        comments = row.get("评论", 0) or 0
        engagement = calculate_engagement_rate(row)
        md_content += f"| {title} | {views} | {likes} | {collects} | {comments} | {engagement}% |\n"
    
    with open(out_dir / "report.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"📄 报告已保存：{out_dir}")
    return out_dir


def cmd_fetch():
    """获取并分析数据"""
    print("=" * 60)
    print("📊 小红书发布数据追踪")
    print("=" * 60)
    
    rows = fetch_content_data()
    if not rows:
        return
    
    analysis = analyze_performance(rows)
    print("\n📈 数据分析完成:")
    print(f"   总笔记：{analysis.get('total_notes', 0)}")
    print(f"   总观看：{analysis.get('total_views', 0)}")
    print(f"   总点赞：{analysis.get('total_likes', 0)}")
    print(f"   平均互动率：{analysis.get('avg_engagement_rate', 0)}%")
    
    record_to_tracker(rows)
    out_dir = save_report(analysis, rows)
    
    print("\n" + "=" * 60)
    print("✅ 数据追踪完成")
    print("=" * 60)
    print(f"📂 报告目录：{out_dir}")


def cmd_report():
    """显示最新报告"""
    # 查找最新报告
    reports = sorted(OUTPUT_BASE.glob("report_*"), reverse=True)
    if not reports:
        print("❌ 暂无报告")
        return
    
    latest = reports[0]
    report_file = latest / "report.md"
    
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"❌ 报告文件不存在：{report_file}")


def main():
    parser = argparse.ArgumentParser(description="小红书发布数据追踪")
    parser.add_argument("--check", action="store_true", help="健康检查")
    
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("fetch", help="获取并分析数据")
    sub.add_parser("report", help="显示最新报告")
    
    args = parser.parse_args()
    
    if args.check:
        checks = [
            {"name": "cdp_publish.py", "status": "ok" if CDP_SCRIPT.is_file() else "warn"},
            {"name": "tracker.py", "status": "ok" if TRACKER_SCRIPT.is_file() else "warn"},
        ]
        print(json.dumps({"skill": "xhs-analytics", "checks": checks}, indent=2))
        return
    
    if args.command == "fetch":
        cmd_fetch()
    elif args.command == "report":
        cmd_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
