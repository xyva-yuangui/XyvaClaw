#!/usr/bin/env python3
"""
web-scraper 基础版 - 网页抓取脚本
基于 requests + BeautifulSoup 实现
"""

import argparse
import json
import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("❌ 缺少依赖：请安装 requests 和 beautifulsoup4")
    print("pip install requests beautifulsoup4")

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "scraping"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_random_headers():
    """获取随机请求头"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

def fetch_url(url, method="GET", data=None, timeout=10, retry=2):
    """抓取URL内容"""
    if not HAS_DEPS:
        return {"error": "依赖未安装"}
    
    headers = get_random_headers()
    
    for attempt in range(retry + 1):
        try:
            # 随机延迟（1-3秒）
            if attempt > 0:
                delay = random.uniform(1, 3)
                time.sleep(delay)
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, data=data, timeout=timeout)
            else:
                return {"error": f"不支持的HTTP方法: {method}"}
            
            response.raise_for_status()
            
            # 检测编码
            if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            return {
                "success": True,
                "url": url,
                "status_code": response.status_code,
                "content": response.text,
                "encoding": response.encoding,
                "headers": dict(response.headers),
                "size": len(response.content)
            }
        
        except requests.exceptions.RequestException as e:
            if attempt == retry:
                return {
                    "success": False,
                    "url": url,
                    "error": f"请求失败: {str(e)}",
                    "attempts": attempt + 1
                }
            continue
    
    return {"success": False, "error": "未知错误"}

def extract_data(html, selectors):
    """从HTML提取数据"""
    if not HAS_DEPS:
        return {"error": "依赖未安装"}
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        results = {}
        
        for key, selector in selectors.items():
            try:
                elements = soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        # 单个元素
                        if elements[0].name in ['img', 'a', 'link']:
                            results[key] = elements[0].get('href') or elements[0].get('src') or elements[0].text.strip()
                        else:
                            results[key] = elements[0].text.strip()
                    else:
                        # 多个元素
                        results[key] = [elem.text.strip() for elem in elements]
                else:
                    results[key] = None
            except Exception as e:
                results[key] = f"选择器错误: {str(e)}"
        
        # 提取所有链接
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        results['_links'] = [link for link in links if link and not link.startswith('#')]
        
        # 提取页面标题
        title = soup.title
        results['_title'] = title.text.strip() if title else None
        
        # 提取meta描述
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        results['_description'] = meta_desc.get('content') if meta_desc else None
        
        return {
            "success": True,
            "data": results,
            "element_count": len(soup.find_all())
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"解析失败: {str(e)}"
        }

def scrape(url, selectors=None, method="GET", data=None, output_file=None):
    """执行抓取"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not output_file:
        # 从URL生成文件名
        parsed = urlparse(url)
        domain = parsed.netloc.replace(':', '_').replace('.', '_')
        output_file = OUTPUT_DIR / f"{domain}_{timestamp}.json"
    else:
        output_file = Path(output_file)
        if not output_file.is_absolute():
            output_file = OUTPUT_DIR / output_file
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 抓取页面
    fetch_result = fetch_url(url, method, data)
    if not fetch_result.get("success"):
        return fetch_result
    
    # 提取数据
    extract_result = None
    if selectors:
        extract_result = extract_data(fetch_result["content"], selectors)
    
    # 构建结果
    result = {
        "success": True,
        "url": url,
        "fetch": fetch_result,
        "extract": extract_result,
        "timestamp": timestamp,
        "output_file": str(output_file)
    }
    
    # 保存结果
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 抓取结果已保存: {output_file}")
    except Exception as e:
        print(f"⚠️ 保存失败: {e}")
        result["save_error"] = str(e)
    
    return result

def main():
    parser = argparse.ArgumentParser(description="网页抓取")
    parser.add_argument("--url", required=True, help="目标URL")
    parser.add_argument("--selector", action="append", help="CSS选择器（格式：key:selector）")
    parser.add_argument("--method", default="GET", choices=["GET", "POST"], help="HTTP方法")
    parser.add_argument("--data", help="POST数据（key=value&key2=value2）")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--check", action="store_true", help="健康检查")
    
    args = parser.parse_args()
    
    if args.check:
        result = {
            "skill": "web-scraper",
            "version": "1.0.0-basic",
            "status": "ok" if HAS_DEPS else "error",
            "dependencies": {
                "requests": "ok" if 'requests' in sys.modules else "missing",
                "beautifulsoup4": "ok" if 'bs4' in sys.modules else "missing"
            },
            "output_dir": str(OUTPUT_DIR),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if HAS_DEPS else 1
    
    # 解析选择器
    selectors = {}
    if args.selector:
        for sel in args.selector:
            if ':' in sel:
                key, selector = sel.split(':', 1)
                selectors[key.strip()] = selector.strip()
            else:
                selectors[f"selector_{len(selectors)}"] = sel
    
    # 解析POST数据
    data = None
    if args.data:
        data = {}
        for pair in args.data.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                data[k] = v
    
    # 执行抓取
    result = scrape(
        url=args.url,
        selectors=selectors if selectors else None,
        method=args.method,
        data=data,
        output_file=args.output
    )
    
    # 输出结果
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1

if __name__ == "__main__":
    sys.exit(main())