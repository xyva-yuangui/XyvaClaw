---
name: browser-pilot
triggers: 
version: 1.0.0
status: enhanced
description: 增强版浏览器自动化。基于 Playwright 实现完整浏览器操作，包括基础导航、截图、点击、表单填写、内容提取、文件上传/下载、多标签页管理。支持反检测和高级自动化。
provides: 
os: 
clawdbot: 
emoji: 🌐
category: automation
priority: high
updated: 2026-03-11
---

# 🌐 browser-pilot（增强版）

✅ **状态**：增强版已上线，功能完整。

## 功能

### 基础操作
1. **导航** (navigate) - 访问 URL
2. **截图** (screenshot) - 页面截图（支持整页）
3. **点击** (click) - 点击元素
4. **填写** (fill) - 填写表单
5. **提取文本** (extract_text) - 提取页面/元素文本
6. **提取 HTML** (extract_html) - 提取页面/元素 HTML
7. **等待** (wait) - 等待指定时间

### 增强功能（新增）
8. **文件上传** (upload_file) - 上传文件到表单
9. **文件下载** (download_file) - 下载文件
10. **多标签页** (switch_tab/new_tab/close_tab) - 标签页管理

### 浏览器支持
- Chromium（Chrome）
- Firefox
- WebKit（Safari）

### 反检测
- 隐藏 webdriver 特征
- 隐藏 automation 特征
- 随机 User-Agent
- 模拟人类操作延迟

## 使用方法

### 通过技能调用
用户说"打开网页"、"截图"、"自动化操作"时自动触发。

### 直接脚本调用
```bash
# 健康检查
python3 scripts/browse.py --check

# 访问网页
python3 scripts/browse.py --url "https://example.com"

# 访问网页并截图
python3 scripts/browse.py --url "https://example.com" --screenshot

# 访问网页并提取文本
python3 scripts/browse.py --url "https://example.com" --extract "h1"

# 有头模式（显示浏览器窗口）
python3 scripts/browse.py --url "https://example.com" --headed

# 自定义延迟
python3 scripts/browse.py --url "https://example.com" --slow-mo 500
```

### Python API 调用
```python
from browse import BrowserPilot

with BrowserPilot(headless=True, slow_mo=100) as pilot:
    # 启动
    pilot.start("chromium")
    
    # 导航
    pilot.navigate("https://example.com")
    
    # 截图
    pilot.screenshot("output.png")
    
    # 点击
    pilot.click("#login-button")
    
    # 填写表单
    pilot.fill("#username", "myuser")
    pilot.fill("#password", "mypass")
    
    # 提取文本
    text = pilot.extract_text("h1")
    print(text["text"])
    
    # 关闭（with 语句自动关闭）
```

## 技术实现

基于 `playwright` Python 库实现，提供同步 API。

## 安装

```bash
# 安装 playwright
pip install playwright

# 安装浏览器
playwright install
```

## 限制

1. 基础功能，不支持高级操作（如文件上传、下载）
2. 无头模式默认开启（可切换有头）
3. 单页面操作（不支持多标签页）

## 开发计划

- **今天 18:00**：基础版完成 ✅
- **明天**：增强版（文件上传/下载、多标签页、动作录制）
- **本周内**：高级反检测、代理支持

## 输出目录

截图和输出文件保存到：`/Users/momo/.openclaw/output/browser/`
