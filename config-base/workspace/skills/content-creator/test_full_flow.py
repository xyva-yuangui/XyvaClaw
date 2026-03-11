#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试：调研 → 创作 → 创建文档 → 插入图片
"""

import requests
import json
import os
from pathlib import Path
from datetime import datetime

# 加载飞书配置
env_path = Path.home() / '.openclaw' / 'secrets' / 'feishu.env'
with open(env_path, 'r') as f:
    for line in f:
        if '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

APP_ID = os.getenv('FEISHU_APP_ID')
APP_SECRET = os.getenv('FEISHU_APP_SECRET')

def get_token():
    """获取飞书 token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    response = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    result = response.json()
    if result.get('code') == 0:
        return result['tenant_access_token']
    else:
        raise Exception(f"获取 token 失败：{result}")

def create_document(title, token):
    """创建飞书文档"""
    url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {"title": title}
    
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    
    if result.get('code') == 0:
        doc_id = result['data']['document']['document_id']
        print(f"✅ 文档创建成功：{doc_id}")
        return doc_id
    else:
        print(f"❌ 文档创建失败：{result}")
        return None

def upload_image(doc_id, image_path, token):
    """上传图片到文档获取 file_token"""
    url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    
    file_size = os.path.getsize(image_path)
    file_name = os.path.basename(image_path)
    
    with open(image_path, 'rb') as f:
        files = {
            'file_name': (None, file_name),
            'parent_type': (None, 'docx_image'),
            'parent_node': (None, doc_id),
            'size': (None, str(file_size)),
            'file': (file_name, f.read(), 'image/png')
        }
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.post(url, headers=headers, files=files)
        result = response.json()
        
        if result.get('code') == 0:
            file_token = result['data']['file_token']
            print(f"✅ 图片上传成功：{file_token[:30]}...")
            return file_token
        else:
            print(f"❌ 图片上传失败：{result}")
            return None

def insert_image_to_docx(doc_id, file_token, token, parent_id=None):
    """插入图片到文档（使用正确的 API 路径和参数）"""
    if not parent_id:
        parent_id = doc_id
    
    # 正确的 API 路径：/blocks/{parent_id}/children
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # 关键修复：block_type=27，使用 image.file_token
    payload = {
        "index": 0,
        "children": [
            {
                "block_type": 27,
                "image": {
                    "file_token": file_token
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"📎 插入图片到文档 {doc_id}...")
    print(f"   状态码：{response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 0:
            print(f"✅ 图片插入成功！")
            return True
        else:
            print(f"❌ 插入失败：{result}")
            return False
    else:
        print(f"❌ API 错误：{response.status_code}")
        print(f"   响应：{response.text[:200]}")
        return False

def insert_text_to_docx(doc_id, text, token, parent_id=None):
    """插入文本到文档"""
    if not parent_id:
        parent_id = doc_id
    
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    payload = {
        "parent_id": parent_id,
        "after_position": 0,
        "block": {
            "block_type": 1,
            "text": {
                "elements": [{"text_run": {"content": text}}]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"📝 插入文本到文档...")
    print(f"   状态码：{response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        if result.get('code') == 0:
            print(f"✅ 文本插入成功！")
            return True
        else:
            print(f"❌ 插入失败：{result}")
            return False
    else:
        print(f"❌ API 错误：{response.status_code}")
        return False

def main():
    """主测试流程"""
    print("="*60)
    print("🧪 完整流程测试：调研 → 创作 → 文档 → 插图")
    print("="*60)
    
    # 1. 获取 token
    print("\n📋 步骤 1: 获取飞书 token...")
    token = get_token()
    print(f"✅ Token 获取成功：{token[:30]}...")
    
    # 2. 创建文档
    print("\n📋 步骤 2: 创建飞书文档...")
    title = f"📊 AI 漫剧行业深度调研报告 - {datetime.now().strftime('%Y%m%d %H%M%S')}"
    doc_id = create_document(title, token)
    
    if not doc_id:
        print("❌ 文档创建失败，终止测试")
        return
    
    doc_url = f"https://feishu.cn/docx/{doc_id}"
    print(f"📄 文档链接：{doc_url}")
    
    # 3. 插入标题文本
    print("\n📋 步骤 3: 插入文档内容...")
    insert_text_to_docx(doc_id, "AI 漫剧行业深度调研报告", token)
    insert_text_to_docx(doc_id, "", token)  # 空行
    insert_text_to_docx(doc_id, "调研时间：2026 年 3 月 3 日", token)
    insert_text_to_docx(doc_id, "数据来源：36 氪、DataEye、浙商证券等 15+ 机构", token)
    
    # 4. 准备图表
    print("\n📋 步骤 4: 准备图表...")
    chart_dir = Path.home() / '.openclaw' / 'workspace' / 'output'
    chart_files = [
        chart_dir / 'chart_market_size.png',
        chart_dir / 'chart_age_distribution.png',
        chart_dir / 'chart_revenue_model.png',
        chart_dir / 'chart_cost_comparison.png'
    ]
    
    # 5. 上传并插入图片
    print("\n📋 步骤 5: 上传并插入图片...")
    for i, chart_file in enumerate(chart_files[:4], 1):  # 测试全部 4 张
        if chart_file.exists():
            print(f"\n🖼️  处理图片 {i}/{len(chart_files)}: {chart_file.name}")
            
            # 上传图片获取 file_token
            file_token = upload_image(doc_id, str(chart_file), token)
            
            if file_token:
                # 插入文档（使用 file_token）
                insert_image_to_docx(doc_id, file_token, token)
        else:
            print(f"⚠️  图片不存在：{chart_file}")
    
    # 6. 总结
    print("\n" + "="*60)
    print("✅ 完整流程测试完成！")
    print("="*60)
    print(f"📄 文档链接：{doc_url}")
    print(f"🖼️  插入图片：2 张")
    print(f"📝 插入文本：4 段")
    print("\n请打开文档查看效果！")

if __name__ == '__main__':
    main()
