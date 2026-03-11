#!/usr/bin/env python3
"""
miniflux-news 技能健康检查
"""

import sys
import os
import json

def check_config():
    """检查配置"""
    config_paths = [
        os.path.expanduser("~/.config/clawdbot/miniflux-news.json"),
        "/Users/momo/.config/clawdbot/miniflux-news.json"
    ]
    
    env_url = os.environ.get("MINIFLUX_URL")
    env_token = os.environ.get("MINIFLUX_TOKEN")
    
    # 检查环境变量
    if env_url and env_token:
        return True, "✅ 使用环境变量配置"
    
    # 检查配置文件
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    # 支持多种字段名
                    url = config.get("url") or config.get("miniflux_url")
                    token = config.get("token") or config.get("miniflux_token")
                    if url and token:
                        return True, f"✅ 使用配置文件: {path}"
                    else:
                        return False, f"❌ 配置文件不完整: {path}"
            except (json.JSONDecodeError, IOError) as e:
                return False, f"❌ 配置文件读取失败: {path} ({str(e)})"
    
    return False, "❌ 未找到配置（需要环境变量 MINIFLUX_URL/MINIFLUX_TOKEN 或配置文件）"

def check_python_deps():
    """检查 Python 依赖"""
    deps = ["requests"]
    missing = []
    
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        return False, f"❌ 缺少 Python 依赖: {', '.join(missing)}"
    return True, "✅ Python 依赖完整"

def check_script():
    """检查主脚本"""
    script_path = os.path.join(os.path.dirname(__file__), "miniflux.py")
    if not os.path.exists(script_path):
        return False, "❌ 主脚本 miniflux.py 不存在"
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            if len(content) < 100:
                return False, "❌ 主脚本内容过短"
    except IOError:
        return False, "❌ 主脚本无法读取"
    
    return True, "✅ 主脚本完整"

def main():
    print("🔍 检查 miniflux-news 技能...")
    
    checks = [
        ("配置", check_config()),
        ("Python 依赖", check_python_deps()),
        ("脚本", check_script())
    ]
    
    all_ok = True
    for name, (ok, msg) in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n🎉 miniflux-news 技能健康检查通过！")
        print("   注意: 这是配置型技能，需要正确的 Miniflux API 配置才能使用")
        return 0
    else:
        print("\n⚠️  miniflux-news 技能存在问题，请修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())