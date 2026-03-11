#!/usr/bin/env python3
"""
smart-messenger 技能健康检查
"""

import sys
import os
import json

def check_templates():
    """检查消息模板"""
    skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(skill_dir, "templates")
    
    if not os.path.exists(templates_dir):
        return False, "❌ templates 目录不存在"
    
    template_files = [f for f in os.listdir(templates_dir) if f.endswith(".json")]
    if not template_files:
        return False, "❌ templates 目录为空"
    
    # 检查模板文件格式
    valid_templates = []
    invalid_templates = []
    
    for template_file in template_files:
        template_path = os.path.join(templates_dir, template_file)
        try:
            with open(template_path, 'r') as f:
                template = json.load(f)
                if "id" in template and "name" in template:
                    valid_templates.append(template["id"])
                else:
                    invalid_templates.append(template_file)
        except (json.JSONDecodeError, IOError):
            invalid_templates.append(template_file)
    
    if invalid_templates:
        return False, f"❌ 模板文件格式错误: {', '.join(invalid_templates)}"
    
    return True, f"✅ 模板文件完整 ({len(valid_templates)} 个模板)"

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
    script_path = os.path.join(os.path.dirname(__file__), "send_message.py")
    if not os.path.exists(script_path):
        return False, "❌ 主脚本 send_message.py 不存在"
    
    try:
        with open(script_path, 'r') as f:
            content = f.read()
            if len(content) < 100:
                return False, "❌ 主脚本内容过短"
    except IOError:
        return False, "❌ 主脚本无法读取"
    
    return True, "✅ 主脚本完整"

def check_feishu_config():
    """检查飞书配置（可选）"""
    # 这个技能依赖飞书通道配置，但配置在 OpenClaw 层面
    # 这里只检查是否有飞书相关的环境变量或配置
    env_vars = ["FEISHU_APP_ID", "FEISHU_APP_SECRET"]
    found_vars = [var for var in env_vars if var in os.environ]
    
    if found_vars:
        return True, f"✅ 找到飞书环境变量: {', '.join(found_vars)}"
    else:
        return True, "⚠️  未找到飞书环境变量（可能使用其他配置方式）"

def main():
    print("🔍 检查 smart-messenger 技能...")
    
    checks = [
        ("消息模板", check_templates()),
        ("Python 依赖", check_python_deps()),
        ("脚本", check_script()),
        ("飞书配置", check_feishu_config())
    ]
    
    all_ok = True
    for name, (ok, msg) in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg}")
        if not ok:
            all_ok = False
    
    if all_ok:
        print("\n🎉 smart-messenger 技能健康检查通过！")
        print("   注意: 这是配置型技能，需要正确的飞书配置才能发送消息")
        return 0
    else:
        print("\n⚠️  smart-messenger 技能存在问题，请修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())