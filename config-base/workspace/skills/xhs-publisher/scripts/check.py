#!/usr/bin/env python3
"""
xhs-publisher 技能健康检查
"""

import os
import sys
from pathlib import Path

def main():
    print(f"🔍 检查 xhs-publisher 技能...")
    
    skill_dir = Path(__file__).parent.parent
    
    # 检查必需文件
    required_files = ["SKILL.md", "_meta.json"]
    all_ok = True
    
    for file in required_files:
        file_path = skill_dir / file
        if file_path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (缺失)")
            all_ok = False
    
    # 检查scripts目录
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        print(f"  ✅ scripts/目录")
    else:
        print(f"  ⚠️  scripts/目录 (缺失)")
    
    if all_ok:
        print("\n🎉 技能结构检查通过！")
        return 0
    else:
        print("\n🚨 发现问题，请修复")
        return 1

if __name__ == "__main__":
    sys.exit(main())
