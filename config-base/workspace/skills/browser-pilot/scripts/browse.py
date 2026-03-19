#!/usr/bin/env python3
"""
browser-pilot 基础版 - 浏览器自动化脚本
基于 Playwright 实现基础自动化功能
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("⚠️ 警告：playwright 未安装")
    print("请运行：pip install playwright")
    print("然后运行：playwright install")

# 输出目录
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "browser"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 浏览器配置
BROWSER_CONFIG = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "ignore_https_errors": True,
    "java_script_enabled": True,
}

# 反检测配置
STEALTH_CONFIG = {
    "device_scale_factor": 1,
    "has_touch": False,
    "is_mobile": False,
}

class BrowserPilot:
    """浏览器飞行员（基础版）"""
    
    def __init__(self, headless=True, slow_mo=100):
        self.headless = headless
        self.slow_mo = slow_mo  # 操作延迟（毫秒），模拟人类
        self.playwright = None
        self.browser = None
        self.page = None
        self.context = None
    
    def start(self, browser_type="chromium"):
        """启动浏览器"""
        if not HAS_PLAYWRIGHT:
            return {"error": "playwright 未安装"}
        
        try:
            self.playwright = sync_playwright().start()
            
            # 选择浏览器
            if browser_type == "chromium":
                browser_launcher = self.playwright.chromium
            elif browser_type == "firefox":
                browser_launcher = self.playwright.firefox
            elif browser_type == "webkit":
                browser_launcher = self.playwright.webkit
            else:
                return {"error": f"不支持的浏览器类型：{browser_type}"}
            
            # 启动浏览器
            self.browser = browser_launcher.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            
            # 创建上下文（带反检测）
            context_config = BROWSER_CONFIG.copy()
            context_config.update(STEALTH_CONFIG)
            # 移除重复的 viewport
            if "viewport" in context_config:
                del context_config["viewport"]
            
            self.context = self.browser.new_context(
                **context_config,
                color_scheme="light",
            )
            
            # 创建页面
            self.page = self.context.new_page()
            
            # 注入反检测脚本
            self._inject_stealth()
            
            print(f"✅ 浏览器已启动：{browser_type}")
            return {"success": True, "browser": browser_type}
        
        except Exception as e:
            return {"error": f"浏览器启动失败：{str(e)}"}
    
    def _inject_stealth(self):
        """注入反检测脚本"""
        if not self.page:
            return
        
        # 隐藏 webdriver 特征
        self.page.add_init_script("""
            // 隐藏 webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // 隐藏 automation 特征
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // 隐藏 language 特征
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en'],
            });
        """)
    
    def navigate(self, url, wait_until="load", timeout=30000):
        """导航到页面"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        try:
            response = self.page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout
            )
            
            # 等待页面稳定
            time.sleep(0.5 + self.slow_mo / 1000)
            
            return {
                "success": True,
                "url": url,
                "status": response.status,
                "title": self.page.title()
            }
        
        except PlaywrightTimeout:
            return {"error": f"导航超时：{timeout}ms"}
        except Exception as e:
            return {"error": f"导航失败：{str(e)}"}
    
    def screenshot(self, output_path=None, full_page=False):
        """截图"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"screenshot_{timestamp}.png"
        else:
            output_path = Path(output_path)
            if not output_path.is_absolute():
                output_path = OUTPUT_DIR / output_path
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.page.screenshot(
                path=str(output_path),
                full_page=full_page
            )
            
            print(f"✅ 截图已保存：{output_path}")
            return {
                "success": True,
                "output_file": str(output_path)
            }
        
        except Exception as e:
            return {"error": f"截图失败：{str(e)}"}
    
    def click(self, selector, timeout=5000):
        """点击元素"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        try:
            # 等待元素
            self.page.wait_for_selector(selector, timeout=timeout)
            
            # 点击（带延迟）
            time.sleep(self.slow_mo / 1000)
            self.page.click(selector)
            
            # 等待导航（如果有）
            try:
                self.page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass  # 没有导航，继续
            
            return {"success": True, "selector": selector}
        
        except PlaywrightTimeout:
            return {"error": f"元素未找到：{selector}"}
        except Exception as e:
            return {"error": f"点击失败：{str(e)}"}
    
    def fill(self, selector, value, timeout=5000):
        """填写表单"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        try:
            # 等待元素
            self.page.wait_for_selector(selector, timeout=timeout)
            
            # 填写（带延迟）
            time.sleep(self.slow_mo / 1000)
            self.page.fill(selector, value)
            
            return {"success": True, "selector": selector, "value": value}
        
        except PlaywrightTimeout:
            return {"error": f"元素未找到：{selector}"}
        except Exception as e:
            return {"error": f"填写失败：{str(e)}"}
    
    def extract_text(self, selector=None):
        """提取文本"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        try:
            if selector:
                # 提取特定元素
                element = self.page.query_selector(selector)
                if element:
                    text = element.text_content()
                    return {"success": True, "text": text.strip()}
                else:
                    return {"error": f"元素未找到：{selector}"}
            else:
                # 提取整个页面文本
                text = self.page.content()
                # 使用 BeautifulSoup 提取纯文本（如果有）
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                except:
                    pass
                return {"success": True, "text": text[:5000]}  # 限制长度
        
        except Exception as e:
            return {"error": f"提取失败：{str(e)}"}
    
    def extract_html(self, selector=None):
        """提取 HTML"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        try:
            if selector:
                element = self.page.query_selector(selector)
                if element:
                    html = element.inner_html()
                    return {"success": True, "html": html}
                else:
                    return {"error": f"元素未找到：{selector}"}
            else:
                html = self.page.content()
                return {"success": True, "html": html}
        
        except Exception as e:
            return {"error": f"提取失败：{str(e)}"}
    
    def wait(self, seconds=1):
        """等待"""
        time.sleep(seconds)
        return {"success": True, "waited": seconds}
    
    def upload_file(self, selector, file_path):
        """上传文件"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        file_path = Path(file_path)
        if not file_path.exists():
            return {"error": f"文件不存在：{file_path}"}
        
        try:
            # 等待文件输入元素
            self.page.wait_for_selector(selector, timeout=5000)
            
            # 上传文件
            self.page.set_input_files(selector, str(file_path))
            
            return {"success": True, "selector": selector, "file": str(file_path)}
        
        except PlaywrightTimeout:
            return {"error": f"元素未找到：{selector}"}
        except Exception as e:
            return {"error": f"上传失败：{str(e)}"}
    
    def download_file(self, selector=None, download_path=None):
        """下载文件"""
        if not self.page:
            return {"error": "浏览器未启动"}
        
        if not download_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            download_path = OUTPUT_DIR / f"download_{timestamp}"
        else:
            download_path = Path(download_path)
        
        download_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # 设置下载路径
            self.context.set_default_timeout(30000)  # 30秒超时
            
            # 如果有选择器，点击下载
            if selector:
                self.page.wait_for_selector(selector, timeout=5000)
                with self.page.expect_download() as download_info:
                    self.page.click(selector)
                download = download_info.value
            else:
                # 等待下载开始
                with self.page.expect_download() as download_info:
                    pass  # 等待外部触发的下载
                download = download_info.value
            
            # 保存文件
            save_path = download_path / download.suggested_filename
            download.save_as(str(save_path))
            
            return {
                "success": True,
                "file": str(save_path),
                "size": save_path.stat().st_size if save_path.exists() else 0
            }
        
        except Exception as e:
            return {"error": f"下载失败：{str(e)}"}
    
    def switch_tab(self, index=0):
        """切换标签页"""
        if not self.context:
            return {"error": "浏览器未启动"}
        
        try:
            tabs = self.context.pages
            if 0 <= index < len(tabs):
                self.page = tabs[index]
                return {"success": True, "tab_index": index, "total_tabs": len(tabs)}
            else:
                return {"error": f"标签页索引超出范围：{index}（共{len(tabs)}个）"}
        except Exception as e:
            return {"error": f"切换标签页失败：{str(e)}"}
    
    def new_tab(self, url=None):
        """新建标签页"""
        if not self.context:
            return {"error": "浏览器未启动"}
        
        try:
            new_page = self.context.new_page()
            self.page = new_page
            
            if url:
                nav_result = self.navigate(url)
                if not nav_result.get("success"):
                    return nav_result
            
            return {"success": True, "url": url}
        except Exception as e:
            return {"error": f"新建标签页失败：{str(e)}"}
    
    def close_tab(self, index=None):
        """关闭标签页"""
        if not self.context:
            return {"error": "浏览器未启动"}
        
        try:
            tabs = self.context.pages
            if index is None:
                # 关闭当前标签页
                if len(tabs) > 1:
                    self.page.close()
                    self.page = tabs[-2]  # 切换到前一个标签页
                else:
                    return {"error": "不能关闭最后一个标签页"}
            elif 0 <= index < len(tabs):
                # 关闭指定标签页
                tabs[index].close()
                if self.page == tabs[index]:
                    # 如果关闭的是当前页，切换到第一个标签页
                    self.page = tabs[0] if tabs else None
            else:
                return {"error": f"标签页索引超出范围：{index}"}
            
            return {"success": True, "remaining_tabs": len(self.context.pages)}
        except Exception as e:
            return {"error": f"关闭标签页失败：{str(e)}"}
    
    def close(self):
        """关闭浏览器"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            print("✅ 浏览器已关闭")
            return {"success": True}
        except Exception as e:
            return {"error": f"关闭失败：{str(e)}"}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def browse_url(url, screenshot=False, extract_selector=None, output_dir=None):
    """快速浏览 URL（便捷函数）"""
    result = {
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
    
    with BrowserPilot(headless=True, slow_mo=100) as pilot:
        # 启动
        start_result = pilot.start()
        if not start_result.get("success"):
            return {"error": start_result.get("error")}
        
        # 导航
        nav_result = pilot.navigate(url)
        if not nav_result.get("success"):
            return nav_result
        
        result["title"] = nav_result.get("title")
        result["status"] = nav_result.get("status")
        
        # 截图
        if screenshot:
            screenshot_result = pilot.screenshot()
            result["screenshot"] = screenshot_result.get("output_file")
        
        # 提取文本
        if extract_selector:
            extract_result = pilot.extract_text(extract_selector)
            result["extracted_text"] = extract_result.get("text")
        
        # 提取页面文本（前 1000 字符）
        page_text = pilot.extract_text()
        result["page_text_preview"] = page_text.get("text", "")[:1000]
    
    return result

def main():
    parser = argparse.ArgumentParser(description="browser-pilot 基础版")
    parser.add_argument("--url", "-u", help="要访问的 URL")
    parser.add_argument("--screenshot", "-s", action="store_true", help="截图")
    parser.add_argument("--extract", "-e", help="CSS 选择器提取文本")
    parser.add_argument("--headless", action="store_true", default=True, help="无头模式（默认开启）")
    parser.add_argument("--headed", action="store_true", help="有头模式（显示浏览器窗口）")
    parser.add_argument("--slow-mo", type=int, default=100, help="操作延迟（毫秒）")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--check", action="store_true", help="健康检查")
    
    args = parser.parse_args()
    
    if args.check:
        result = {
            "skill": "browser-pilot",
            "version": "1.0.0-basic",
            "status": "ok" if HAS_PLAYWRIGHT else "warn",
            "playwright_installed": HAS_PLAYWRIGHT,
            "output_dir": str(OUTPUT_DIR),
            "features": [
                "navigate", "screenshot", "click", "fill",
                "extract_text", "extract_html", "wait"
            ],
            "browsers": ["chromium", "firefox", "webkit"],
            "timestamp": datetime.now().isoformat()
        }
        
        if not HAS_PLAYWRIGHT:
            result["install_command"] = "pip install playwright && playwright install"
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if HAS_PLAYWRIGHT else 1
    
    if not args.url:
        parser.print_help()
        return 1
    
    if args.headed:
        args.headless = False
    
    # 浏览 URL
    result = browse_url(
        args.url,
        screenshot=args.screenshot,
        extract_selector=args.extract,
        output_dir=args.output
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") or "url" in result else 1

if __name__ == "__main__":
    sys.exit(main())
