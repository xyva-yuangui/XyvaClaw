#!/usr/bin/env python3
"""browser-pilot 健康检查"""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

def health_check():
    checks = []
    
    # 检查 playwright
    try:
        import playwright
        # playwright 没有__version__，尝试从包元数据获取
        try:
            from importlib.metadata import version
            pw_version = version("playwright")
        except:
            pw_version = "unknown"
        checks.append({
            "name": "playwright",
            "status": "ok",
            "message": f"已安装 (版本：{pw_version})"
        })
    except ImportError:
        checks.append({
            "name": "playwright",
            "status": "error",
            "message": "未安装，运行：pip install playwright"
        })
    
    # 检查浏览器安装
    browser_status = "warn"
    browser_msg = "浏览器可能未安装"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # 检查 Chromium
            if p.chromium:
                browser_status = "ok"
                browser_msg = "Chromium 可用"
    except Exception as e:
        browser_msg = f"浏览器检查失败：{str(e)}"
    
    checks.append({
        "name": "browsers",
        "status": browser_status,
        "message": browser_msg
    })
    
    # 检查输出目录
    output_dir = Path.home() / ".openclaw" / "output" / "browser"
    if output_dir.exists():
        checks.append({
            "name": "output_dir",
            "status": "ok",
            "message": f"输出目录：{output_dir}"
        })
    else:
        checks.append({
            "name": "output_dir",
            "status": "warn",
            "message": "输出目录不存在，将自动创建"
        })
    
    # 检查脚本文件
    script_path = Path(__file__).parent / "browse.py"
    if script_path.exists():
        checks.append({
            "name": "browse.py",
            "status": "ok",
            "message": "主脚本存在"
        })
    else:
        checks.append({
            "name": "browse.py",
            "status": "error",
            "message": "主脚本缺失"
        })
    
    # 检查依赖
    for mod in ["asyncio", "pathlib"]:
        try:
            __import__(mod)
            checks.append({"name": mod, "status": "ok"})
        except ImportError:
            checks.append({"name": mod, "status": "error"})
    
    # 总体状态
    status = "ok"
    if any(c["status"] == "error" for c in checks):
        status = "error"
    elif any(c["status"] == "warn" for c in checks):
        status = "warn"
    
    return {
        "skill": "browser-pilot",
        "version": "1.0.0-basic",
        "status": status,
        "checks": checks,
        "features": [
            "navigate", "screenshot", "click", "fill",
            "extract_text", "extract_html", "wait"
        ],
        "browsers": ["chromium", "firefox", "webkit"],
        "timestamp": datetime.now().isoformat(),
        "note": "基础版本，支持基础浏览器自动化。"
    }

if __name__ == "__main__":
    if "--check" in sys.argv:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "error" else 1)
    else:
        print("Usage: python check.py --check")
        sys.exit(1)
