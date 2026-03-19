#!/usr/bin/env python3
"""
python-dataviz 技能健康检查
"""

import sys
import os
import subprocess

def check_venv():
    """检查虚拟环境"""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_dir = os.path.join(skill_dir, ".venv")
    
    if not os.path.exists(venv_dir):
        return False, "❌ 虚拟环境不存在 (需要运行: python3 -m venv .venv)"
    
    # 检查激活脚本
    activate_scripts = [
        os.path.join(venv_dir, "bin", "activate"),
        os.path.join(venv_dir, "Scripts", "activate.bat")  # Windows
    ]
    
    has_activate = any(os.path.exists(script) for script in activate_scripts)
    if not has_activate:
        return False, "❌ 虚拟环境不完整"
    
    return True, "✅ 虚拟环境存在"

def check_python_deps():
    """检查 Python 依赖"""
    deps = ["matplotlib", "seaborn", "plotly", "pandas", "numpy"]
    missing = []
    
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        return False, f"❌ 缺少 Python 依赖: {', '.join(missing)}"
    return True, "✅ Python 依赖完整"

def check_requirements():
    """检查 requirements.txt 或 pyproject.toml"""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyproject = os.path.join(skill_dir, "pyproject.toml")
    requirements = os.path.join(skill_dir, "requirements.txt")
    
    if os.path.exists(pyproject):
        try:
            with open(pyproject, 'r') as f:
                content = f.read()
                if "[project]" in content or "[tool.poetry]" in content:
                    return True, "✅ 使用 pyproject.toml 配置"
        except IOError:
            pass
    
    if os.path.exists(requirements):
        try:
            with open(requirements, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if len(lines) > 0:
                    return True, "✅ 使用 requirements.txt 配置"
        except IOError:
            pass
    
    return False, "❌ 未找到依赖配置文件"

def check_example_scripts():
    """检查示例脚本"""
    scripts_dir = os.path.dirname(__file__)
    expected_scripts = ["bar_chart.py", "line_chart.py", "scatter_plot.py", "heatmap.py", "distribution.py"]
    
    missing = []
    for script in expected_scripts:
        if not os.path.exists(os.path.join(scripts_dir, script)):
            missing.append(script)
    
    if missing:
        return False, f"❌ 缺少示例脚本: {', '.join(missing)}"
    return True, "✅ 示例脚本完整"

def main():
    print("🔍 检查 python-dataviz 技能...")
    
    checks = [
        ("虚拟环境", check_venv()),
        ("Python 依赖", check_python_deps()),
        ("依赖配置", check_requirements()),
        ("示例脚本", check_example_scripts())
    ]
    
    all_ok = True
    for name, (ok, msg) in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n🎉 python-dataviz 技能健康检查通过！")
        print("   注意: 这是一个高级技能，需要 Python 数据科学环境")
        return 0
    else:
        print("\n⚠️  python-dataviz 技能存在问题，请修复")
        print("   建议: 1) 创建虚拟环境 2) 安装依赖 3) 测试示例脚本")
        return 1

if __name__ == "__main__":
    sys.exit(main())