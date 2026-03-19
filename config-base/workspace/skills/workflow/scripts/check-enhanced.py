#!/usr/bin/env python3
"""
workflow 技能增强健康检查
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    """检查所有依赖工具"""
    print("🔧 检查依赖工具...")
    
    dependencies = {
        "jq": "JSON处理工具",
        "yq": "YAML处理工具", 
        "curl": "HTTP请求工具",
        "uuidgen": "UUID生成工具",
        "flock": "文件锁工具"
    }
    
    # 添加util-linux路径
    import os
    util_linux_path = "/opt/homebrew/opt/util-linux/bin"
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{util_linux_path}:{original_path}"
    
    all_ok = True
    for tool, desc in dependencies.items():
        path = shutil.which(tool)
        if path:
            print(f"  ✅ {tool}: {desc} ({path})")
        else:
            # 特别检查flock
            if tool == "flock":
                flock_path = "/opt/homebrew/opt/util-linux/bin/flock"
                if os.path.exists(flock_path):
                    print(f"  ✅ {tool}: {desc} ({flock_path})")
                else:
                    print(f"  ❌ {tool}: {desc} (未安装)")
                    all_ok = False
            else:
                print(f"  ❌ {tool}: {desc} (未安装)")
                all_ok = False
    
    return all_ok

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
    
    # 检查scripts目录
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        print(f"  ✅ scripts/目录")
        for script in scripts_dir.glob("*.py"):
            print(f"    📜 {script.name}")
    else:
        print(f"  ❌ scripts/目录 (缺失)")
        all_ok = False
    
    # 检查examples目录
    examples_dir = skill_dir / "examples"
    if examples_dir.exists():
        print(f"  ✅ examples/目录")
        for example in examples_dir.iterdir():
            if example.is_dir():
                print(f"    📂 {example.name}")
    else:
        print(f"  ⚠️  examples/目录 (缺失)")
    
    return all_ok

def check_example_workflow():
    """检查示例工作流"""
    print("\n🧪 检查示例工作流...")
    
    skill_dir = Path(__file__).parent.parent
    example_dir = skill_dir / "examples" / "daily-stock-report"
    
    if not example_dir.exists():
        print("  ⚠️  示例工作流目录不存在")
        return False
    
    required_example_files = [
        "README.md",
        "flow.md", 
        "config.yaml",
        "run.sh"
    ]
    
    all_ok = True
    for file in required_example_files:
        file_path = example_dir / file
        if file_path.exists():
            print(f"  ✅ {file}")
            
            # 检查文件权限
            if file == "run.sh":
                if os.access(file_path, os.X_OK):
                    print(f"    🔧 run.sh 可执行")
                else:
                    print(f"    ⚠️  run.sh 需要执行权限: chmod +x {file_path}")
        else:
            print(f"  ❌ {file} (缺失)")
            all_ok = False
    
    # 检查state和logs目录
    for subdir in ["state", "logs"]:
        subdir_path = example_dir / subdir
        if subdir_path.exists():
            print(f"  ✅ {subdir}/目录")
        else:
            print(f"  ⚠️  {subdir}/目录 (缺失，运行时创建)")
    
    return all_ok

def test_yq_installation():
    """测试yq是否可用"""
    print("\n🧪 测试yq功能...")
    
    test_yaml = """
name: test
version: 1.0.0
dependencies:
  - jq
  - curl
"""
    
    try:
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(test_yaml)
            temp_file = f.name
        
        # 测试yq读取
        result = subprocess.run(
            ["yq", ".name", temp_file],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"  ✅ yq 功能正常: {result.stdout.strip()}")
            os.unlink(temp_file)
            return True
        else:
            print(f"  ❌ yq 读取失败: {result.stderr}")
            os.unlink(temp_file)
            return False
            
    except Exception as e:
        print(f"  ❌ yq 测试异常: {str(e)}")
        return False

def test_jq_installation():
    """测试jq是否可用"""
    print("\n🧪 测试jq功能...")
    
    test_json = '{"name": "test", "version": "1.0.0"}'
    
    try:
        result = subprocess.run(
            ["jq", ".name"],
            input=test_json,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"  ✅ jq 功能正常: {result.stdout.strip()}")
            return True
        else:
            print(f"  ❌ jq 处理失败: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"  ❌ jq 测试异常: {str(e)}")
        return False

def main():
    print("🔍 workflow 技能增强健康检查")
    print("=" * 50)
    
    # 检查依赖
    deps_ok = check_dependencies()
    
    # 检查结构
    struct_ok = check_structure()
    
    # 检查示例
    example_ok = check_example_workflow()
    
    # 测试工具功能
    yq_ok = True
    jq_ok = True
    
    if shutil.which("yq"):
        yq_ok = test_yq_installation()
    
    if shutil.which("jq"):
        jq_ok = test_jq_installation()
    
    print("\n" + "=" * 50)
    print("📊 检查总结:")
    
    issues = []
    
    if not deps_ok:
        issues.append("❌ 依赖工具不完整")
    
    if not struct_ok:
        issues.append("❌ 目录结构不完整")
    
    if not example_ok:
        issues.append("⚠️  示例工作流不完整")
    
    if not yq_ok:
        issues.append("❌ yq 功能异常")
    
    if not jq_ok:
        issues.append("❌ jq 功能异常")
    
    if issues:
        print("\n🚨 发现问题:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n🔧 修复建议:")
        if "依赖工具不完整" in issues or "yq 功能异常" in issues:
            print("  1. 安装缺失依赖: brew install yq")
            print("  2. flock工具可能需要: brew install flock 或使用其他文件锁方案")
        
        if "目录结构不完整" in issues:
            print("  3. 检查并修复缺失的文件")
        
        if "示例工作流不完整" in issues:
            print("  4. 完善示例工作流文件")
        
        return 1
    else:
        print("🎉 workflow 技能检查全部通过！")
        print("\n✅ 技能状态: 健康")
        print("✅ 依赖工具: 完整")
        print("✅ 目录结构: 完整")
        print("✅ 示例工作流: 完整")
        print("✅ 工具功能: 正常")
        return 0

if __name__ == "__main__":
    sys.exit(main())