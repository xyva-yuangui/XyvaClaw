#!/usr/bin/env python3
"""
web-scraper 增强版 - 网页抓取脚本
支持会话管理、增强反爬虫、XPath提取、基础并发
"""

import argparse
import json
import os
import sys
import time
import random
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, urljoin
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from bs4 import BeautifulSoup
    import lxml.html  # 用于XPath
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    print("❌ 缺少依赖：请安装 requests, beautifulsoup4, lxml")
    print("pip install requests beautifulsoup4 lxml")

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "scraping"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 会话存储目录
SESSION_DIR = Path.home() / ".openclaw" / "sessions" / "web-scraper"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

# User-Agent 列表（扩展版）
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

class SessionManager:
    """会话管理器"""
    
    def __init__(self, session_name="default"):
        self.session_name = session_name
        self.session_file = SESSION_DIR / f"{session_name}.json"
        self.session = requests.Session()
        self.load_session()
    
    def get_random_headers(self):
        """获取随机请求头（增强版）"""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def load_session(self):
        """加载会话"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 恢复cookies
                    if 'cookies' in data:
                        for cookie in data['cookies']:
                            self.session.cookies.set(**cookie)
                    # 恢复headers
                    if 'headers' in data:
                        self.session.headers.update(data['headers'])
                print(f"✅ 已加载会话: {self.session_name}")
            except Exception as e:
                print(f"⚠️ 会话加载失败: {e}")
    
    def save_session(self):
        """保存会话"""
        try:
            data = {
                'cookies': [
                    {
                        'name': c.name,
                        'value': c.value,
                        'domain': c.domain,
                        'path': c.path,
                    }
                    for c in self.session.cookies
                ],
                'headers': dict(self.session.headers),
                'timestamp': datetime.now().isoformat()
            }
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ 已保存会话: {self.session_name}")
        except Exception as e:
            print(f"⚠️ 会话保存失败: {e}")
    
    def clear_session(self):
        """清除会话"""
        self.session = requests.Session()
        if self.session_file.exists():
            self.session_file.unlink()
        print(f"✅ 已清除会话: {self.session_name}")
    
    def fetch(self, url, method="GET", data=None, timeout=15, retry=3, 
              delay_range=(1, 3), use_proxy=False, proxy=None):
        """增强版抓取（支持延迟、重试、代理）"""
        if not HAS_DEPS:
            return {"error": "依赖未安装"}
        
        # 设置请求头
        headers = self.get_random_headers()
        self.session.headers.update(headers)
        
        # 设置代理
        if use_proxy and proxy:
            self.session.proxies = {'http': proxy, 'https': proxy}
        
        for attempt in range(retry + 1):
            try:
                # 随机延迟（模拟人类行为）
                if attempt > 0:
                    delay = random.uniform(*delay_range)
                    time.sleep(delay)
                
                # 添加随机延迟（即使第一次请求）
                if random.random() < 0.3:  # 30%概率添加小延迟
                    time.sleep(random.uniform(0.5, 1.5))
                
                if method.upper() == "GET":
                    response = self.session.get(url, timeout=timeout)
                elif method.upper() == "POST":
                    response = self.session.post(url, data=data, timeout=timeout)
                else:
                    return {"error": f"不支持的HTTP方法: {method}"}
                
                response.raise_for_status()
                
                # 检测编码
                if response.encoding is None or response.encoding.lower() == 'iso-8859-1':
                    response.encoding = response.apparent_encoding or 'utf-8'
                
                # 检测反爬虫
                if self._detect_anti_scraping(response):
                    print(f"⚠️ 检测到反爬虫机制，尝试绕过...")
                    # 可以在这里添加更多绕过策略
                
                result = {
                    "success": True,
                    "url": url,
                    "status_code": response.status_code,
                    "content": response.text,
                    "encoding": response.encoding,
                    "headers": dict(response.headers),
                    "size": len(response.content),
                    "attempts": attempt + 1,
                    "cookies": len(self.session.cookies)
                }
                
                # 保存会话
                self.save_session()
                return result
            
            except requests.exceptions.RequestException as e:
                if attempt == retry:
                    return {
                        "success": False,
                        "url": url,
                        "error": f"请求失败: {str(e)}",
                        "attempts": attempt + 1
                    }
                print(f"⚠️ 第{attempt+1}次尝试失败: {e}")
                continue
        
        return {"success": False, "error": "未知错误"}
    
    def _detect_anti_scraping(self, response):
        """检测反爬虫机制"""
        content = response.text.lower()
        
        # 常见反爬虫关键词
        anti_keywords = [
            'access denied', 'forbidden', 'robot', 'captcha',
            'cloudflare', 'distil', 'imperva', 'akamai',
            'please enable javascript', 'security check'
        ]
        
        for keyword in anti_keywords:
            if keyword in content:
                return True
        
        # 检查状态码
        if response.status_code in [403, 429, 503]:
            return True
        
        return False

class DataExtractor:
    """数据提取器（支持CSS、XPath、正则）"""
    
    def __init__(self, html):
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser') if html else None
        self.tree = lxml.html.fromstring(html) if html else None
    
    def extract_css(self, selectors):
        """CSS选择器提取"""
        if not self.soup:
            return {"error": "HTML未解析"}
        
        results = {}
        for key, selector in selectors.items():
            try:
                elements = self.soup.select(selector)
                if elements:
                    if len(elements) == 1:
                        # 单个元素
                        elem = elements[0]
                        if elem.name in ['img', 'a', 'link', 'script']:
                            results[key] = elem.get('href') or elem.get('src') or elem.get('content') or elem.text.strip()
                        else:
                            results[key] = elem.text.strip()
                    else:
                        # 多个元素
                        results[key] = [elem.text.strip() for elem in elements]
                else:
                    results[key] = None
            except Exception as e:
                results[key] = f"CSS选择器错误: {str(e)}"
        
        return results
    
    def extract_xpath(self, xpaths):
        """XPath提取"""
        if not self.tree:
            return {"error": "HTML未解析为XPath树"}
        
        results = {}
        for key, xpath in xpaths.items():
            try:
                elements = self.tree.xpath(xpath)
                if elements:
                    if len(elements) == 1:
                        # 单个元素
                        elem = elements[0]
                        if isinstance(elem, str):
                            results[key] = elem.strip()
                        else:
                            results[key] = elem.text_content().strip() if hasattr(elem, 'text_content') else str(elem)
                    else:
                        # 多个元素
                        results[key] = [
                            elem.text_content().strip() if hasattr(elem, 'text_content') else str(elem)
                            for elem in elements
                        ]
                else:
                    results[key] = None
            except Exception as e:
                results[key] = f"XPath错误: {str(e)}"
        
        return results
    
    def extract_regex(self, patterns):
        """正则表达式提取"""
        results = {}
        for key, pattern in patterns.items():
            try:
                matches = re.findall(pattern, self.html, re.DOTALL | re.IGNORECASE)
                if matches:
                    if len(matches) == 1:
                        results[key] = matches[0].strip()
                    else:
                        results[key] = [match.strip() for match in matches]
                else:
                    results[key] = None
            except Exception as e:
                results[key] = f"正则表达式错误: {str(e)}"
        
        return results
    
    def extract_metadata(self):
        """提取页面元数据"""
        metadata = {}
        
        if self.soup:
            # 标题
            title = self.soup.title
            metadata['title'] = title.text.strip() if title else None
            
            # Meta描述
            meta_desc = self.soup.find('meta', attrs={'name': 'description'})
            metadata['description'] = meta_desc.get('content') if meta_desc else None
            
            # Meta关键词
            meta_keywords = self.soup.find('meta', attrs={'name': 'keywords'})
            metadata['keywords'] = meta_keywords.get('content') if meta_keywords else None
            
            # 所有链接
            links = [a.get('href') for a in self.soup.find_all('a', href=True)]
            metadata['links'] = [urljoin(self.soup.base.get('href', ''), link) if self.soup.base else link 
                                for link in links if link and not link.startswith('#')]
            
            # 图片
            images = [img.get('src') for img in self.soup.find_all('img', src=True)]
            metadata['images'] = [urljoin(self.soup.base.get('href', ''), img) if self.soup.base else img 
                                 for img in images if img]
        
        return metadata

class ConcurrentScraper:
    """并发抓取器"""
    
    def __init__(self, max_workers=3, delay_range=(1, 3)):
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.session_manager = SessionManager("concurrent")
    
    def scrape_urls(self, urls, selectors=None, method="GET", data=None):
        """并发抓取多个URL"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_url = {
                executor.submit(
                    self._scrape_single,
                    url, selectors, method, data, i
                ): url
                for i, url in enumerate(urls)
            }
            
            # 收集结果
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "url": url,
                        "success": False,
                        "error": str(e)
                    })
        
        return results
    
    def _scrape_single(self, url, selectors, method, data, index):
        """单个URL抓取（用于并发）"""
        # 添加索引相关的延迟，避免同时发起请求
        time.sleep(index * random.uniform(*self.delay_range) / self.max_workers)
        
        # 抓取
        fetch_result = self.session_manager.fetch(
            url, method, data, 
            delay_range=self.delay_range
        )
        
        if not fetch_result.get("success"):
            return {
                "url": url,
                "success": False,
                "error": fetch_result.get("error", "未知错误")
            }
        
        # 提取数据
        extract_result = None
        if selectors:
            extractor = DataExtractor(fetch_result["content"])
            
            # 根据选择器类型自动选择提取方法
            if any('//' in sel for sel in selectors.values()):
                # 包含XPath
                extract_result = extractor.extract_xpath(selectors)
            elif any(re.search(r'\(.*\)', sel) for sel in selectors.values()):
                # 包含正则
                extract_result = extractor.extract_regex(selectors)
            else:
                # CSS选择器
                extract_result = extractor.extract_css(selectors)
        
        return {
            "url": url,
            "success": True,
            "fetch": fetch_result,
            "extract": extract_result
        }

def scrape_enhanced(url, selectors=None, method="GET", data=None, 
                   session_name="default", output_file=None,
                   use_concurrent=False, concurrent_urls=None,
                   extract_method="auto", xpath_selectors=None,
                   regex_patterns=None, save_session=True):
    """增强版抓取函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if not output_file:
        parsed = urlparse(url)
        domain = parsed.netloc.replace(':', '_').replace('.', '_')
        output_file = OUTPUT_DIR / f"{domain}_{timestamp}.json"
    else:
        output_file = Path(output_file)
        if not output_file.is_absolute():
            output_file = OUTPUT_DIR / output_file
    
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 初始化会话管理器
    session_manager = SessionManager(session_name)
    
    # 并发抓取
    if use_concurrent and concurrent_urls:
        scraper = ConcurrentScraper(max_workers=3)
        results = scraper.scrape_urls(concurrent_urls, selectors, method, data)
        
        result = {
            "success": True,
            "mode": "concurrent",
            "urls": concurrent_urls,
            "results": results,
            "timestamp": timestamp,
            "output_file": str(output_file)
        }
    
    else:
        # 单URL抓取
        fetch_result = session_manager.fetch(url, method, data)
        
        if not fetch_result.get("success"):
            return fetch_result
        
        # 数据提取
        extract_result = None
        if selectors or xpath_selectors or regex_patterns:
            extractor = DataExtractor(fetch_result["content"])
            
            # 合并所有选择器
            all_results = {}
            
            # CSS选择器
            if selectors:
                css_results = extractor.extract_css(selectors)
                all_results.update(css_results)
            
            # XPath选择器
            if xpath_selectors:
                xpath_results = extractor.extract_xpath(xpath_selectors)
                all_results.update({f"xpath_{k}": v for k, v in xpath_results.items()})
            
            # 正则表达式
            if regex_patterns:
                regex_results = extractor.extract_regex(regex_patterns)
                all_results.update({f"regex_{k}": v for k, v in regex_results.items()})
            
            # 元数据
            metadata = extractor.extract_metadata()
            all_results.update({f"meta_{k}": v for k, v in metadata.items()})
            
            extract_result = {
                "success": True,
                "data": all_results,
                "element_count": len(extractor.soup.find_all()) if extractor.soup else 0
            }
        
        # 构建结果
        result = {
            "success": True,
            "url": url,
            "session": session_name,
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
    
    return result