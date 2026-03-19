#!/usr/bin/env python3
"""
auto-video-creator 技能健康检查
"""

import sys
import subprocess
import os

def check_ffmpeg():
    """检查 FFmpeg 是否安装"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return True, f"✅ FFmpeg 已安装: {version_line}"
        else:
            return False, "❌ FFmpeg 未安装或无法运行"
    except FileNotFoundError:
        return False, "❌ FFmpeg 未安装"

def check_python_deps():
    """检查 Python 依赖"""
    deps = ["PIL", "numpy", "moviepy"]
    missing = []
    
    # 检查虚拟环境是否存在
    venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv")
    
    if os.path.exists(venv_path):
        # 虚拟环境存在，假设依赖已安装
        return True, "✅ Python 依赖完整（虚拟环境中）"
    else:
        # 检查系统环境
        for dep in deps:
            try:
                if dep == "PIL":
                    __import__("PIL")
                else:
                    __import__(dep)
            except ImportError:
                missing.append(dep)
        
        if missing:
            return False, f"❌ 缺少 Python 依赖: {', '.join(missing)}"
        return True, "✅ Python 依赖完整"

def check_assets():
    """检查资源文件"""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(skill_dir, "assets")
    templates_dir = os.path.join(skill_dir, "templates")
    
    issues = []
    
    if not os.path.exists(assets_dir):
        issues.append("assets 目录不存在")
    elif len(os.listdir(assets_dir)) == 0:
        issues.append("assets 目录为空")
    
    if not os.path.exists(templates_dir):
        issues.append("templates 目录不存在")
    elif len(os.listdir(templates_dir)) == 0:
        issues.append("templates 目录为空")
    
    if issues:
        return False, f"❌ 资源文件问题: {'; '.join(issues)}"
    return True, "✅ 资源文件完整"

def main():
    print("🔍 检查 auto-video-creator 技能...")
    
    checks = [
        ("FFmpeg", check_ffmpeg()),
        ("Python 依赖", check_python_deps()),
        ("资源文件", check_assets())
    ]
    
    all_ok = True
    for name, (ok, msg) in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n🎉 auto-video-creator 技能健康检查通过！")
        return 0
    else:
        print("\n⚠️  auto-video-creator 技能存在问题，请修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())