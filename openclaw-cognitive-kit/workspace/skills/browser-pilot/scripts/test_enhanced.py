#!/usr/bin/env python3
"""
测试 browser-pilot 增强功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from browse import BrowserPilot

def test_enhanced_features():
    """测试增强功能"""
    print("🧪 测试 browser-pilot 增强功能")
    
    with BrowserPilot(headless=True, slow_mo=100) as pilot:
        # 1. 启动浏览器
        start_result = pilot.start()
        if not start_result.get("success"):
            print(f"❌ 浏览器启动失败: {start_result.get('error')}")
            return False
        
        print("✅ 浏览器启动成功")
        
        # 2. 导航到测试页面
        test_page = Path(__file__).parent.parent / "test_page.html"
        nav_result = pilot.navigate(f"file://{test_page}")
        if not nav_result.get("success"):
            print(f"❌ 导航失败: {nav_result.get('error')}")
            return False
        
        print(f"✅ 导航成功: {nav_result.get('title', 'N/A')}")
        
        # 3. 测试文件上传（模拟）
        print("\n📤 测试文件上传...")
        # 创建一个测试文件
        test_file = Path(__file__).parent / "test_upload.txt"
        test_file.write_text("这是 browser-pilot 测试上传文件\n生成时间: 2026-03-11")
        
        upload_result = pilot.upload_file("#file-input", str(test_file))
        if upload_result.get("success"):
            print(f"✅ 文件上传测试通过: {upload_result['file']}")
        else:
            print(f"⚠️ 文件上传测试: {upload_result.get('error', '未知错误')}")
        
        # 4. 测试多标签页
        print("\n📑 测试多标签页...")
        new_tab_result = pilot.new_tab("https://httpbin.org/html")
        if new_tab_result.get("success"):
            print(f"✅ 新建标签页成功")
            
            # 切换回第一个标签页
            switch_result = pilot.switch_tab(0)
            if switch_result.get("success"):
                print(f"✅ 切换标签页成功: 标签页 {switch_result['tab_index'] + 1}")
            else:
                print(f"⚠️ 切换标签页: {switch_result.get('error')}")
        else:
            print(f"⚠️ 新建标签页: {new_tab_result.get('error')}")
        
        # 5. 测试文件下载（模拟点击）
        print("\n📥 测试文件下载...")
        # 点击下载按钮
        click_result = pilot.click("button[onclick='downloadFile()']")
        if click_result.get("success"):
            print("✅ 下载按钮点击成功")
            # 等待下载（实际需要更复杂的处理）
            pilot.wait(2)
        else:
            print(f"⚠️ 下载按钮点击: {click_result.get('error')}")
        
        # 6. 截图
        print("\n📸 测试截图...")
        screenshot_result = pilot.screenshot("test_enhanced.png")
        if screenshot_result.get("success"):
            print(f"✅ 截图保存: {screenshot_result['output_file']}")
        else:
            print(f"⚠️ 截图: {screenshot_result.get('error')}")
        
        # 7. 提取文本
        print("\n📝 测试文本提取...")
        text_result = pilot.extract_text("h1")
        if text_result.get("success"):
            print(f"✅ 提取标题: {text_result['text']}")
        else:
            print(f"⚠️ 文本提取: {text_result.get('error')}")
        
        # 8. 关闭标签页
        print("\n❌ 测试关闭标签页...")
        close_result = pilot.close_tab(1)  # 关闭第二个标签页
        if close_result.get("success"):
            print(f"✅ 关闭标签页成功，剩余 {close_result['remaining_tabs']} 个标签页")
        else:
            print(f"⚠️ 关闭标签页: {close_result.get('error')}")
        
        print("\n" + "="*50)
        print("✅ browser-pilot 增强功能测试完成")
        return True

if __name__ == "__main__":
    success = test_enhanced_features()
    sys.exit(0 if success else 1)
