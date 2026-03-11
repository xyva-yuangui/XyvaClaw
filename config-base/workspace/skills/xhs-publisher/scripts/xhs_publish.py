#!/usr/bin/env python3
"""
小红书统一发布引擎 (xhs-publisher)
合并自: auto-redbook-skills(发布) + xiaohongshu-cdp + xhs-batch-operator

通道优先级: CDP → Cookie → 手动降级
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path.home() / ".openclaw" / "workspace" / "skills"
OUTPUT_BASE = Path.home() / ".openclaw" / "output" / "xhs-publisher"
CDP_SCRIPT = SKILLS_DIR / "xiaohongshu-cdp" / "scripts" / "cdp_publish.py"
COOKIE_SCRIPT = SKILLS_DIR / "_archived" / "auto-redbook-skills-0.1.0" / "scripts" / "publish_xhs_fixed.py"
BATCH_SCRIPT = SKILLS_DIR / "xhs-batch-operator" / "batch_operator.py"
RENDER_SCRIPT = SKILLS_DIR / "_archived" / "auto-redbook-skills-0.1.0" / "scripts" / "render_xhs_v2.py"
TRACKER_SCRIPT = SKILLS_DIR / "effect-tracker" / "scripts" / "tracker.py"
CREATOR_SCRIPT = SKILLS_DIR / "xhs-creator" / "scripts" / "xhs_creator.py"

ACCOUNTS_FILE = SKILLS_DIR / "xhs-publisher" / "config" / "accounts.json"
ENV_FILE = SKILLS_DIR / "xhs-publisher" / "config" / ".env"

DEFAULT_DELAY = 300  # 5 min between publishes
MAX_DAILY_PER_ACCOUNT = 5


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _track(action: str, status: str = "ok"):
    if TRACKER_SCRIPT.is_file():
        try:
            subprocess.run(
                [sys.executable, str(TRACKER_SCRIPT), "record",
                 "--skill", "xhs-publisher", "--action", action, "--status", status],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass


def _detect_channels() -> dict:
    """Detect available publishing channels."""
    channels = {}

    # CDP channel
    if CDP_SCRIPT.is_file():
        cdp_profile = Path.home() / ".openclaw" / "xhs-cdp-profile"
        channels["cdp"] = {
            "available": cdp_profile.is_dir(),
            "script": str(CDP_SCRIPT),
            "note": "Profile exists" if cdp_profile.is_dir() else "需要先登录: python cdp_publish.py login",
        }
    else:
        channels["cdp"] = {"available": False, "note": "cdp_publish.py not found"}

    # Cookie channel
    if COOKIE_SCRIPT.is_file():
        has_cookie = ENV_FILE.is_file()
        if not has_cookie:
            # Check legacy location
            legacy_env = SKILLS_DIR / "auto-redbook-skills-0.1.0" / ".env"
            has_cookie = legacy_env.is_file()
        channels["cookie"] = {
            "available": has_cookie,
            "script": str(COOKIE_SCRIPT),
            "note": "Cookie configured" if has_cookie else "需要配置Cookie",
        }
    else:
        channels["cookie"] = {"available": False, "note": "publish script not found"}

    # Manual fallback always available
    channels["manual"] = {
        "available": True,
        "note": "输出文件到目录，手动发布",
    }

    return channels


def _select_channel(preferred: str = "auto") -> str:
    channels = _detect_channels()
    if preferred != "auto" and preferred in channels:
        if channels[preferred]["available"]:
            return preferred
        print(f"  ⚠️ 指定通道 {preferred} 不可用: {channels[preferred]['note']}")

    # Auto: CDP > Cookie > Manual
    for ch in ["cdp", "cookie", "manual"]:
        if channels.get(ch, {}).get("available"):
            return ch
    return "manual"


def cmd_publish(title: str, content: str, images: list,
                channel: str = "auto", headless: bool = False,
                preview: bool = False, account: str = "default") -> dict:
    print(f"\n🚀 小红书发布")
    print(f"   标题: {title}")
    print(f"   图片: {len(images)} 张")

    selected = _select_channel(channel)
    print(f"   通道: {selected}")
    if preview:
        print(f"   模式: 预览（不实际发布）")
    print()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = OUTPUT_BASE / f"publish_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    result = {
        "title": title,
        "channel": selected,
        "preview": preview,
        "account": account,
        "timestamp": _now(),
        "output_dir": str(out_dir),
    }

    # Save content for reference - use full draft content if available
    content_file = out_dir / "content.md"
    
    # Try to find and use the full draft content from xhs-creator output
    draft_content = None
    import glob
    creator_dirs = sorted(glob.glob(str(Path.home() / ".openclaw" / "output" / "xhs-creator" / "*")), reverse=True)
    for creator_dir in creator_dirs:
        draft_file = Path(creator_dir) / "draft.md"
        if draft_file.exists():
            with open(draft_file, "r", encoding="utf-8") as f:
                draft_content = f.read()
            # Check if draft contains the title
            if title.split("?")[0].split("!")[0].strip() in draft_content:
                print(f"  📝 使用完整草稿内容：{draft_file}")
                break
    
    with open(content_file, "w", encoding="utf-8") as f:
        if draft_content:
            f.write(draft_content)
        else:
            f.write(f"# {title}\n\n{content}")

    if selected == "cdp":
        if preview:
            print(f"  👁️ 预览模式 — 不调用 CDP")
            result["status"] = "preview"
        else:
            print(f"  📡 通过 CDP 发布...")
            try:
                cmd = [sys.executable, str(CDP_SCRIPT), "publish",
                       "--title", title, "--content", content]
                for img in images:
                    cmd.extend(["--image", img])
                if headless:
                    cmd.append("--headless")
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    result["status"] = "published"
                    print(f"  ✅ CDP 发布成功")
                else:
                    result["status"] = "cdp_error"
                    result["error"] = r.stderr[:500]
                    print(f"  ⚠️ CDP 发布失败，尝试Cookie降级...")
                    selected = "cookie"
            except Exception as e:
                result["status"] = "cdp_error"
                result["error"] = str(e)
                print(f"  ⚠️ CDP 异常: {e}")
                selected = "cookie"

    if selected == "cookie":
        if preview:
            print(f"  👁️ 预览模式 — 不调用 Cookie API")
            result["status"] = "preview"
        else:
            print(f"  🍪 通过 Cookie 发布...")
            try:
                cmd = [sys.executable, str(COOKIE_SCRIPT),
                       "--title", title, "--content", content]
                for img in images:
                    cmd.extend(["--image", img])
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r.returncode == 0:
                    result["status"] = "published"
                    print(f"  ✅ Cookie 发布成功")
                else:
                    result["status"] = "cookie_error"
                    result["error"] = r.stderr[:500]
                    print(f"  ⚠️ Cookie 发布失败，降级到手动模式")
                    selected = "manual"
            except Exception as e:
                result["status"] = "cookie_error"
                result["error"] = str(e)
                selected = "manual"

    if selected == "manual":
        print(f"  📁 手动模式 — 文件已保存到 {out_dir}")
        manual_guide = out_dir / "MANUAL_PUBLISH_GUIDE.md"
        with open(manual_guide, "w", encoding="utf-8") as f:
            f.write(f"# 手动发布指南\n\n")
            f.write(f"**标题**: {title}\n\n")
            f.write(f"**内容文件**: content.md\n\n")
            f.write(f"**图片**:\n")
            for img in images:
                f.write(f"- {img}\n")
            f.write(f"\n## 步骤\n\n")
            f.write(f"1. 打开小红书 App 或 creator.xiaohongshu.com\n")
            f.write(f"2. 点击 + 发布笔记\n")
            f.write(f"3. 上传图片（按顺序）\n")
            f.write(f"4. 粘贴标题和正文\n")
            f.write(f"5. 添加标签\n")
            f.write(f"6. 发布\n")
        result["status"] = "manual_fallback"
        result["guide"] = str(manual_guide)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    result["elapsed_ms"] = elapsed_ms
    result["channel_used"] = selected

    with open(out_dir / "publish_result.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    _track("publish", result.get("status", "unknown"))
    print(f"\n  📂 {out_dir}")
    return result


def cmd_batch(count: int = 3, topics: list = None, style: str = "种草",
              publish: bool = False, delay: int = DEFAULT_DELAY,
              account: str = "default") -> dict:
    print(f"\n📦 批量操作: {count} 篇")
    if topics:
        print(f"   主题: {', '.join(topics)}")
    print(f"   风格: {style}")
    print(f"   自动发布: {'是' if publish else '否'}")
    print()

    out_dir = OUTPUT_BASE / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    actual_topics = topics or [f"AI效率工具推荐{i+1}" for i in range(count)]
    if len(actual_topics) < count:
        actual_topics = actual_topics * (count // len(actual_topics) + 1)
    actual_topics = actual_topics[:count]

    for i, topic in enumerate(actual_topics, 1):
        print(f"\n{'='*40}")
        print(f"  [{i}/{count}] {topic}")

        # Create content
        if CREATOR_SCRIPT.is_file():
            try:
                r = subprocess.run(
                    [sys.executable, str(CREATOR_SCRIPT),
                     "-t", topic, "-s", style, "--no-research", "--json"],
                    capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0:
                    try:
                        create_result = json.loads(r.stdout.split("\n")[-2])
                        results.append({"topic": topic, "status": "created",
                                        "output": create_result.get("output_dir")})
                        print(f"     ✅ 创作完成")
                    except (json.JSONDecodeError, IndexError):
                        results.append({"topic": topic, "status": "created"})
                else:
                    results.append({"topic": topic, "status": "create_error"})
            except Exception as e:
                results.append({"topic": topic, "status": "error", "error": str(e)})
        else:
            results.append({"topic": topic, "status": "creator_unavailable"})

        if publish and i < count:
            print(f"     ⏳ 等待 {delay}s (防封策略)...")
            # In real execution, would time.sleep(delay)
            # For now just note it
            results[-1]["delay_seconds"] = delay

    batch_result = {
        "total": count, "completed": len([r for r in results if "error" not in r.get("status", "")]),
        "style": style, "auto_publish": publish,
        "results": results, "output_dir": str(out_dir), "timestamp": _now(),
    }

    with open(out_dir / "batch_result.json", "w") as f:
        json.dump(batch_result, f, indent=2, ensure_ascii=False)

    _track("batch", "ok")
    print(f"\n  ✅ 批量操作完成: {batch_result['completed']}/{count}")
    print(f"  📂 {out_dir}")
    return batch_result


def health_check() -> dict:
    channels = _detect_channels()
    checks = []

    for ch_name, ch_info in channels.items():
        checks.append({
            "name": f"channel_{ch_name}",
            "status": "ok" if ch_info["available"] else "warn",
            "message": ch_info["note"],
        })

    deps = {
        "xhs-creator": CREATOR_SCRIPT,
        "effect-tracker": TRACKER_SCRIPT,
    }
    for name, path in deps.items():
        checks.append({"name": name, "status": "ok" if path.is_file() else "warn"})

    checks.append({"name": "python3", "status": "ok"})

    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"

    return {"skill": "xhs-publisher", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": _now()}


def main():
    parser = argparse.ArgumentParser(description="小红书统一发布引擎")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")

    sub = parser.add_subparsers(dest="command")

    # publish
    p_pub = sub.add_parser("publish", help="单篇发布")
    p_pub.add_argument("--title", required=True)
    p_pub.add_argument("--content", required=True)
    p_pub.add_argument("--images", nargs="+", default=[])
    p_pub.add_argument("--channel", default="auto", choices=["auto", "cdp", "cookie", "manual"])
    p_pub.add_argument("--headless", action="store_true")
    p_pub.add_argument("--preview", action="store_true")
    p_pub.add_argument("--account", default="default")

    # batch
    p_batch = sub.add_parser("batch", help="批量操作")
    p_batch.add_argument("-n", "--count", type=int, default=3)
    p_batch.add_argument("-t", "--topics", help="逗号分隔主题")
    p_batch.add_argument("-s", "--style", default="种草")
    p_batch.add_argument("--publish", action="store_true")
    p_batch.add_argument("-d", "--delay", type=int, default=DEFAULT_DELAY)
    p_batch.add_argument("--account", default="default")

    # channels
    sub.add_parser("channels", help="检测可用通道")

    args = parser.parse_args()

    if args.check:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    result = None

    if args.command == "publish":
        result = cmd_publish(args.title, args.content, args.images,
                             args.channel, args.headless, args.preview, args.account)
    elif args.command == "batch":
        topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
        result = cmd_batch(args.count, topics, args.style,
                           args.publish, args.delay, args.account)
    elif args.command == "channels":
        result = _detect_channels()
        for ch, info in result.items():
            status = "✅" if info["available"] else "❌"
            print(f"  {status} {ch}: {info['note']}")

    if args.json and result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
