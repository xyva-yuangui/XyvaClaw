#!/usr/bin/env python3
"""Qwen Image 技能健康检查"""
import sys
import os
from pathlib import Path

# 使用绝对路径
base_dir = Path("~/.xyvaclaw/workspace/skills/qwen-image")

# 检查脚本是否存在
script_path = base_dir / "scripts" / "generate_image.py"
if not script_path.exists():
    print(f"❌ generate_image.py 不存在：{script_path}")
    sys.exit(1)

# 检查 SKILL.md
skill_md = base_dir / "SKILL.md"
if not skill_md.exists():
    print(f"❌ SKILL.md 不存在：{skill_md}")
    sys.exit(1)

# 检查 API Key 配置
api_key = os.environ.get('DASHSCOPE_API_KEY', '')
if not api_key:
    print("⚠️ 警告：DASHSCOPE_API_KEY 未设置")
else:
    print("✅ API Key 已配置")

print("✅ OK - qwen-image")
print("   支持的模型：wan2.6-t2i, wan2.2-t2i-flash, wan2.5-t2i-preview 等")
