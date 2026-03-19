#!/usr/bin/env python3
"""
web-scraper 健康检查
"""

import json
import sys
from datetime import datetime

def health_check():
    checks = []
    
    # 检查脚本文件
    import os
    script_path = os.path.join(os.path.dirname(__file__), "scraper.py")
    if os.path.exists(script_path):
        checks.append({"name": "scraper.py", "status": "ok", "message": "主脚本存在"})
    else:
        checks.append({"name": "scraper.py", "status": "error", "message": "主脚本缺失"})
    
    # 检查输出目录
    output_dir = os.path.expanduser("~/.openclaw/output/scraping")
    if os.path.exists(output_dir):
        checks.append({"name": "output_dir", "status": "ok", "message": f"输出目录: {output_dir}"})
    else:
        checks.append({"name": "output_dir", "status": "warn", "message": "输出目录不存在，将自动创建"})
    
    # 检查依赖
    try:
        import requests
        checks.append({"name": "requests", "status": "ok", "message": f"版本: {requests.__version__}"})
    except ImportError:
        checks.append({"name": "requests", "status": "error", "message": "未安装，功能不可用"})
    
    try:
        from bs4 import BeautifulSoup
        checks.append({"name": "beautifulsoup4", "status": "ok", "message": "可用"})
    except ImportError:
        checks.append({"name": "beautifulsoup4", "status": "error", "message": "未安装，功能不可用"})
    
    # 测试网络连接
    try:
        import requests
        test_response = requests.get("https://httpbin.org/get", timeout=5)
        if test_response.status_code == 200:
            checks.append({"name": "network", "status": "ok", "message": "网络连接正常"})
        else:
            checks.append({"name": "network", "status": "warn", "message": f"测试请求返回: {test_response.status_code}"})
    except Exception as e:
        checks.append({"name": "network", "status": "warn", "message": f"网络测试失败: {str(e)}"})
    
    # 总体状态
    status = "ok"
    if any(c["status"] == "error" for c in checks):
        status = "error"
    elif any(c["status"] == "warn" for c in checks):
        status = "warn"
    
    return {
        "skill": "web-scraper",
        "version": "1.0.0-basic",
        "status": status,
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
        "note": "基础版本，功能有限。完整版正在开发中。"
    }

if __name__ == "__main__":
    if "--check" in sys.argv:
        result = health_check()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "error" else 1)
    
    print("web-scraper 技能健康检查")
    print("用法: python check.py --check")