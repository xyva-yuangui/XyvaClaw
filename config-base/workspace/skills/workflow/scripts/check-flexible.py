#!/usr/bin/env python3
"""
workflow 技能灵活健康检查
支持依赖降级方案
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies_flexible():
    """灵活检查依赖工具"""
    print("🔧 检查依赖工具（灵活模式）...")
    
    dependencies = {
        "jq": {"required": True, "desc": "JSON处理工具"},
        "yq": {"required": False, "desc": "YAML处理工具，可用pyyaml替代"},
        "curl": {"required": True, "desc": "HTTP请求工具"},
        "uuidgen": {"required": True, "desc": "UUID生成工具"},
        "flock": {"required": False, "desc": "文件锁工具，可用其他锁方案"}
    }
    
    all_ok = True
    warnings = []
    
    for tool, info in dependencies.items():
        path = shutil.which(tool)
        if path:
            status = "✅"
        else:
            status = "❌" if info["required"] else "⚠️"
        
        print(f"  {status} {tool}: {info['desc']}")
        
        if not path:
            if info["required"]:
                all_ok = False
                print(f"    错误: {tool} 是必需工具，请安装")
            else:
                warnings.append(f"{tool} 未安装，但可用替代方案")
    
    # 检查Python yaml模块作为yq的替代
    try:
        import yaml
        print("  ✅ pyyaml: YAML处理替代方案")
    except ImportError:
        if not shutil.which("yq"):
            warnings.append("yq和pyyaml都未安装，YAML处理可能受限")
    
    return all_ok, warnings

def check_structure():
    """检查目录结构"""
    print("\n📁 检查目录结构...")
    
    skill_dir = Path(__file__).parent.parent
    required_files = [
        "SKILL.md",
        "components.md",
        "data-flow.md", 
        "errors.md",
        "lifecycle.md",
        "state.md",
        "structure.md"
    ]
    
    all_ok = True
    for file in required_files:
        file_path = skill_dir / file
        if file_path.exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} (缺失)")
            all_ok = False
    
    return all_ok

def test_example_with_fallback():
    """使用降级方案测试示例工作流"""
    print("\n🧪 测试示例工作流（降级模式）...")
    
    skill_dir = Path(__file__).parent.parent
    example_dir = skill_dir / "examples" / "daily-stock-report"
    
    if not example_dir.exists():
        print("  ❌ 示例工作流目录不存在")
        return False
    
    try:
        # 修改run.sh使用Python处理YAML
        run_sh = example_dir / "run.sh"
        with open(run_sh, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否使用yq
        if "yq" in content and not shutil.which("yq"):
            print("  ⚠️  检测到yq使用，但未安装")
            print("     建议: 安装yq或修改脚本使用Python处理YAML")
        
        # 运行示例工作流
        result = subprocess.run(
            ["./run.sh", "--manual"],
            cwd=example_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("  ✅ 示例工作流运行成功")
            
            # 检查输出文件
            output_dir = Path("/Users/momo/.openclaw/workspace/skills/output/reports")
            if output_dir.exists():
                reports = list(output_dir.glob("daily_report_*.md"))
                if reports:
                    print(f"  📄 生成报告: {reports[0].name}")
                    return True
                else:
                    print("  ⚠️  未找到生成的报告文件")
                    return False
            return True
        else:
            print(f"  ❌ 示例工作流运行失败")
            if result.stderr:
                print(f"     错误: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ⚠️  示例工作流超时")
        return False
    except Exception as e:
        print(f"  ❌ 示例工作流异常: {str(e)}")
        return False

def main():
    print("🔍 workflow 技能灵活健康检查")
    print("=" * 50)
    print("模式: 支持依赖降级，优先保证核心功能")
    print("=" * 50)
    
    deps_ok, warnings = check_dependencies_flexible()
    struct_ok = check_structure()
    example_ok = test_example_with_fallback()
    
    print("\n" + "=" * 50)
    print("📊 检查总结:")
    
    core_ok = deps_ok and struct_ok
    
    if core_ok and example_ok:
        print("🎉 workflow 技能核心功能正常！")
        print("✅ 必需依赖: 完整")
        print("✅ 目录结构: 完整")
        print("✅ 示例工作流: 可运行")
        
        if warnings:
            print("\n⚠️  优化建议:")
            for warning in warnings:
                print(f"  • {warning}")
        
        return 0
    else:
        print("🚨 发现问题:")
        
        if not deps_ok:
            print("  ❌ 必需依赖工具缺失")
        
        if not struct_ok:
            print("  ❌ 目录结构不完整")
        
        if not example_ok:
            print("  ❌ 示例工作流不可运行")
        
        print("\n🔧 修复建议:")
        print("  1. 安装必需工具: jq, curl, uuidgen")
        print("  2. 可选安装: yq (或使用Python yaml模块)")
        print("  3. 文件锁: 可使用其他锁方案替代flock")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())