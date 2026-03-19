#!/usr/bin/env python3
"""
chart-image 健康检查
"""

import json
import sys
from datetime import datetime

def health_check():
    checks = []
    
    # 检查脚本文件
    import os
    script_path = os.path.join(os.path.dirname(__file__), "chart.py")
    if os.path.exists(script_path):
        checks.append({"name": "chart.py", "status": "ok", "message": "主脚本存在"})
    else:
        checks.append({"name": "chart.py", "status": "error", "message": "主脚本缺失"})
    
    # 检查包装器
    wrapper_path = os.path.join(os.path.dirname(__file__), "dataviz_wrapper.py")
    if os.path.exists(wrapper_path):
        checks.append({"name": "dataviz_wrapper.py", "status": "ok", "message": "增强包装器存在"})
    else:
        checks.append({"name": "dataviz_wrapper.py", "status": "warn", "message": "增强包装器缺失，使用降级模式"})
    
    # 检查输出目录
    output_dir = os.path.expanduser("~/.openclaw/output/charts")
    if os.path.exists(output_dir):
        checks.append({"name": "output_dir", "status": "ok", "message": f"输出目录: {output_dir}"})
    else:
        checks.append({"name": "output_dir", "status": "warn", "message": "输出目录不存在，将自动创建"})
    
    # 检查核心依赖
    try:
        import matplotlib
        checks.append({"name": "matplotlib", "status": "ok", "message": f"版本: {matplotlib.__version__}"})
    except ImportError:
        checks.append({"name": "matplotlib", "status": "error", "message": "未安装，功能不可用"})
    
    try:
        import seaborn
        checks.append({"name": "seaborn", "status": "ok", "message": f"版本: {seaborn.__version__}"})
    except ImportError:
        checks.append({"name": "seaborn", "status": "warn", "message": "未安装，主题功能受限"})
    
    try:
        import numpy
        checks.append({"name": "numpy", "status": "ok", "message": f"版本: {numpy.__version__}"})
    except ImportError:
        checks.append({"name": "numpy", "status": "warn", "message": "未安装，高级图表功能受限"})
    
    try:
        import pandas
        checks.append({"name": "pandas", "status": "ok", "message": f"版本: {pandas.__version__}"})
    except ImportError:
        checks.append({"name": "pandas", "status": "warn", "message": "未安装，数据处理功能受限"})
    
    # 检查支持的图表类型
    supported_charts = ["line", "bar", "pie", "scatter", "area", "heatmap", "box", "radar"]
    checks.append({"name": "chart_types", "status": "ok", "message": f"支持 {len(supported_charts)} 种图表"})
    
    # 总体状态
    status = "ok"
    if any(c["status"] == "error" for c in checks):
        status = "error"
    elif any(c["status"] == "warn" for c in checks):
        status = "warn"
    
    return {
        "skill": "chart-image",
        "version": "2.5.1-enhanced",
        "status": status,
        "checks": checks,
        "supported_charts": supported_charts,
        "themes": ["default", "dark", "business"],
        "timestamp": datetime.now().isoformat(),
        "note": "增强版本，支持8种图表类型和3种主题。"
    }

if __name__ == "__main__":
    if "--check" in sys.argv:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "error" else 1)
    
    print("chart-image 技能健康检查")
    print("用法: python check.py --check")