#!/usr/bin/env python3
"""
发布后自动质量检查
功能：检查已发布内容是否符合优化配置，生成质量报告
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path.home() / ".openclaw" / "workspace" / "skills"
OUTPUT_BASE = Path.home() / ".openclaw" / "output" / "xhs-publisher"
AUTO_TUNE_CONFIG = SKILLS_DIR / "xhs-creator" / "config" / "auto_tune_config.json"


def load_config():
    """加载优化配置"""
    if AUTO_TUNE_CONFIG.exists():
        with open(AUTO_TUNE_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def check_published_content(publish_dir: Path) -> dict:
    """检查发布内容"""
    result = {
        "publish_dir": str(publish_dir),
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "issues": [],
        "passed": True
    }
    
    config = load_config()
    optimizations = config.get("optimizations", {})
    
    # 检查 1: 标题优化
    if optimizations.get("title_enhancement", {}).get("enabled"):
        content_file = publish_dir / "content.md"
        if content_file.exists():
            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            title_line = [l for l in content.split("\n") if l.startswith("# ") and not l.startswith("## ")]
            if title_line:
                title = title_line[0].replace("# ", "").strip()
                
                # 检查数字
                has_numbers = any(c.isdigit() for c in title)
                # 检查情绪词
                emotion_words = ["必备", "神器", "震惊", "必看", "绝了", "真香"]
                has_emotions = any(word in title for word in emotion_words)
                # 检查疑问句
                has_question = "?" in title or "？" in title
                
                check_result = {
                    "name": "标题优化",
                    "title": title,
                    "has_numbers": has_numbers,
                    "has_emotions": has_emotions,
                    "has_question": has_question,
                    "passed": has_numbers and (has_emotions or has_question)
                }
                result["checks"].append(check_result)
                
                if not check_result["passed"]:
                    result["issues"].append({
                        "type": "标题优化不足",
                        "current": title,
                        "suggestions": []
                    })
                    if not has_numbers:
                        result["issues"][-1]["suggestions"].append("添加数字（如'5 个'、'3 步'）")
                    if not has_emotions:
                        result["issues"][-1]["suggestions"].append("添加情绪词（如'必备'、'神器'）")
                    if not has_question:
                        result["issues"][-1]["suggestions"].append("添加疑问句（如'？'）")
                    result["passed"] = False
    
    # 检查 2: 内容结构
    if optimizations.get("content_structure", {}).get("enabled"):
        content_file = publish_dir / "content.md"
        if content_file.exists():
            with open(content_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            has_list = "清单" in content or "行动清单" in content or any(f"{i}." in content for i in range(1, 6))
            has_steps = "步骤" in content or "第一步" in content or "第二步" in content or "第三步" in content or "1." in content or "2." in content or "3." in content
            
            check_result = {
                "name": "内容结构",
                "has_list": has_list,
                "has_steps": has_steps,
                "passed": has_list or has_steps
            }
            result["checks"].append(check_result)
            
            if not check_result["passed"]:
                result["issues"].append({
                    "type": "内容结构不符合优化配置",
                    "suggestions": ["使用清单体或步骤详解格式"]
                })
                result["passed"] = False
    
    return result


def cmd_check_latest():
    """检查最新发布内容"""
    print("🔍 检查最新发布内容...")
    
    # 查找最新发布目录
    publish_dirs = sorted(OUTPUT_BASE.glob("publish_*"), reverse=True)
    if not publish_dirs:
        print("❌ 未找到发布内容")
        return
    
    latest_dir = publish_dirs[0]
    print(f"📂 发布目录：{latest_dir}")
    
    result = check_published_content(latest_dir)
    
    print("\n📊 检查结果:")
    for check in result["checks"]:
        status = "✅" if check.get("passed") else "❌"
        print(f"  {status} {check['name']}")
        if "title" in check:
            print(f"      标题：{check['title']}")
            if "has_numbers" in check:
                print(f"      数字：{'✅' if check['has_numbers'] else '❌'}")
            if "has_emotions" in check:
                print(f"      情绪词：{'✅' if check['has_emotions'] else '❌'}")
            if "has_question" in check:
                print(f"      疑问句：{'✅' if check['has_question'] else '❌'}")
    
    if result["issues"]:
        print(f"\n⚠️ 发现 {len(result['issues'])} 个问题:")
        for issue in result["issues"]:
            print(f"  - {issue['type']}")
            for suggestion in issue.get("suggestions", []):
                print(f"    → {suggestion}")
    
    print(f"\n{'✅ 通过' if result['passed'] else '❌ 未通过'}")
    
    # 保存检查报告
    report_file = latest_dir / "post_publish_check.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"📄 报告已保存：{report_file}")
    
    return result


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        cmd_check_latest()
    else:
        print("用法：python3 post_publish_check.py [check]")
        print("  check - 检查最新发布内容")


if __name__ == "__main__":
    main()
