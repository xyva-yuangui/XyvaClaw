#!/usr/bin/env python3
"""
web-scraper 增强版 - 命令行接口
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 导入增强版功能
from scraper_enhanced import (
    SessionManager, DataExtractor, ConcurrentScraper,
    scrape_enhanced
)

def main():
    parser = argparse.ArgumentParser(description="web-scraper 增强版")
    parser.add_argument("--url", "-u", help="要抓取的 URL")
    parser.add_argument("--session", "-s", default="default", help="会话名称")
    parser.add_argument("--output", "-o", help="输出文件路径")
    parser.add_argument("--method", "-m", default="GET", help="HTTP 方法")
    parser.add_argument("--data", "-d", help="POST 数据（JSON 格式）")
    parser.add_argument("--css", help="CSS 选择器（JSON 格式）")
    parser.add_argument("--xpath", help="XPath 选择器（JSON 格式）")
    parser.add_argument("--regex", help="正则表达式（JSON 格式）")
    parser.add_argument("--concurrent", action="store_true", help="并发模式")
    parser.add_argument("--urls", nargs="+", help="并发抓取的 URL 列表")
    parser.add_argument("--check", action="store_true", help="健康检查")
    parser.add_argument("--clear-session", action="store_true", help="清除会话")
    parser.add_argument("--list-sessions", action="store_true", help="列出所有会话")
    parser.add_argument("--timeout", type=int, default=15, help="超时时间（秒）")
    parser.add_argument("--retry", type=int, default=3, help="重试次数")
    
    args = parser.parse_args()
    
    # 健康检查
    if args.check:
        try:
            from scraper_enhanced import HAS_DEPS
            result = {
                "skill": "web-scraper",
                "version": "1.0.0-enhanced",
                "status": "ok" if HAS_DEPS else "error",
                "dependencies": {
                    "requests": HAS_DEPS,
                    "beautifulsoup4": HAS_DEPS,
                    "lxml": HAS_DEPS
                },
                "features": [
                    "session_management",
                    "css_extraction",
                    "xpath_extraction",
                    "regex_extraction",
                    "concurrent_scraping",
                    "anti_scraping"
                ],
                "timestamp": datetime.now().isoformat()
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if HAS_DEPS else 1
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return 1
    
    # 清除会话
    if args.clear_session:
        try:
            session = SessionManager(args.session)
            session.clear_session()
            print(f"✅ 会话已清除: {args.session}")
            return 0
        except Exception as e:
            print(f"❌ 清除会话失败: {e}")
            return 1
    
    # 列出会话
    if args.list_sessions:
        try:
            from pathlib import Path
            session_dir = Path.home() / ".openclaw" / "sessions" / "web-scraper"
            if session_dir.exists():
                sessions = [f.stem for f in session_dir.glob("*.json")]
                print(f"📁 可用会话 ({len(sessions)}):")
                for s in sessions:
                    print(f"  - {s}")
                return 0
            else:
                print("📁 无会话文件")
                return 0
        except Exception as e:
            print(f"❌ 列出会话失败: {e}")
            return 1
    
    # 检查 URL
    if not args.url and not args.urls:
        parser.print_help()
        print("\n❌ 必须提供 URL 或 URL 列表")
        return 1
    
    # 解析选择器
    css_selectors = None
    xpath_selectors = None
    regex_patterns = None
    
    if args.css:
        try:
            css_selectors = json.loads(args.css)
        except json.JSONDecodeError as e:
            print(f"❌ CSS 选择器 JSON 格式错误: {e}")
            return 1
    
    if args.xpath:
        try:
            xpath_selectors = json.loads(args.xpath)
        except json.JSONDecodeError as e:
            print(f"❌ XPath 选择器 JSON 格式错误: {e}")
            return 1
    
    if args.regex:
        try:
            regex_patterns = json.loads(args.regex)
        except json.JSONDecodeError as e:
            print(f"❌ 正则表达式 JSON 格式错误: {e}")
            return 1
    
    # 解析 POST 数据
    post_data = None
    if args.data:
        try:
            post_data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"❌ POST 数据 JSON 格式错误: {e}")
            return 1
    
    # 执行抓取
    try:
        if args.concurrent and args.urls:
            # 并发抓取
            result = scrape_enhanced(
                url=args.url or args.urls[0],
                selectors=css_selectors,
                method=args.method,
                data=post_data,
                session_name=args.session,
                output_file=args.output,
                use_concurrent=True,
                concurrent_urls=args.urls,
                xpath_selectors=xpath_selectors,
                regex_patterns=regex_patterns
            )
        else:
            # 单 URL 抓取
            result = scrape_enhanced(
                url=args.url,
                selectors=css_selectors,
                method=args.method,
                data=post_data,
                session_name=args.session,
                output_file=args.output,
                xpath_selectors=xpath_selectors,
                regex_patterns=regex_patterns
            )
        
        if result.get("success"):
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        else:
            print(f"❌ 抓取失败: {result.get('error', '未知错误')}")
            return 1
    
    except Exception as e:
        print(f"❌ 抓取异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
