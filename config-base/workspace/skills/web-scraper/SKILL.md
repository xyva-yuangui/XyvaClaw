---
name: web-scraper
triggers: 
version: 1.0.0
status: enhanced
description: 增强版网页抓取功能。支持会话管理、多模式提取（CSS/XPath/正则）、并发抓取、反爬虫增强。提供完整的命令行接口。
provides: 
os: 
clawdbot: 
emoji: 🕷️
category: data
priority: high
updated: 2026-03-11
---

# 🕷️ web-scraper（增强版）

✅ **状态**：增强版已上线，功能完整。

## 功能

### 核心功能
1. **HTTP 请求**：GET/POST 请求，支持自定义 headers
2. **会话管理**：Cookie 持久化，会话复用
3. **多模式提取**：
   - CSS 选择器提取
   - XPath 表达式提取
   - 正则表达式提取
4. **并发抓取**：多 URL 并发抓取（3个并发）
5. **反爬虫增强**：
   - User-Agent 轮换
   - 请求延迟随机化
   - 代理支持（预留接口）
6. **元数据提取**：自动提取页面标题、描述、链接等

### 输出格式
- JSON 结构化数据
- 保存到 `~/.xyvaclaw/output/scraping/`
- 会话保存到 `~/.xyvaclaw/sessions/web-scraper/`

## 使用方法

### 通过技能调用
用户说"抓取网页"或"提取数据"时自动触发。

### 命令行接口
```bash
# 健康检查
python3 scripts/scraper_cli.py --check

# 基础抓取
python3 scripts/scraper_cli.py --url "https://example.com" --css '{"title": "h1"}'

# 使用会话
python3 scripts/scraper_cli.py --url "https://example.com" --session "my_session"

# XPath 提取
python3 scripts/scraper_cli.py --url "https://example.com" --xpath '{"title": "//h1/text()"}'

# 正则提取
python3 scripts/scraper_cli.py --url "https://example.com" --regex '{"emails": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"}'

# 并发抓取
python3 scripts/scraper_cli.py --urls "https://example1.com" "https://example2.com" --concurrent

# 指定输出文件
python3 scripts/scraper_cli.py --url "https://example.com" --output "result.json"

# 会话管理
python3 scripts/scraper_cli.py --list-sessions
python3 scripts/scraper_cli.py --clear-session --session "old_session"
```

### Python API
```python
from scraper_enhanced import scrape_enhanced, SessionManager, DataExtractor

# 简单抓取
result = scrape_enhanced(
    url="https://example.com",
    selectors={"title": "h1", "content": ".article"},
    session_name="my_session"
)

# 使用会话管理器
session = SessionManager("test_session")
fetch_result = session.fetch("https://example.com")

# 使用数据提取器
extractor = DataExtractor(fetch_result["content"])
css_data = extractor.extract_css({"title": "h1"})
xpath_data = extractor.extract_xpath({"title": "//h1/text()"})
```

## 技术实现

基于 `requests` + `BeautifulSoup4` + `lxml` 实现，提供完整的抓取解决方案。

## 高级功能

1. **会话持久化**：自动保存和加载 Cookie
2. **智能重试**：网络错误自动重试
3. **延迟控制**：随机延迟避免封禁
4. **错误处理**：详细的错误信息和恢复建议
5. **性能监控**：记录抓取时间和大小

## 限制

1. 不支持 JavaScript 渲染页面（需要 browser-pilot）
2. 复杂反爬虫网站可能需要额外配置

## 未来计划

- 集成 Playwright 支持 JavaScript 页面
- 分布式抓取支持
- 智能代理轮换系统