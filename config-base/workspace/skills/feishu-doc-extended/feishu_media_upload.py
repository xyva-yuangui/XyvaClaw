#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书文档媒体上传扩展
功能：上传图片到飞书文档并获取 image_key
"""

import requests
import os
import mimetypes
from pathlib import Path

class FeishuMediaUploader:
    """飞书媒体上传器"""
    
    def __init__(self, tenant_access_token=None, app_id=None, app_secret=None):
        """
        初始化上传器
        
        Args:
            tenant_access_token: 飞书 tenant access token（可选，未传会自动获取）
        """
        self.token = tenant_access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"

    def _load_feishu_env(self):
        """加载 ~/.openclaw/secrets/feishu.env"""
        env_path = os.path.expanduser("~/.openclaw/secrets/feishu.env")
        if not os.path.exists(env_path):
            return

        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

    def _resolve_app_credentials(self):
        """自动解析 app_id/app_secret"""
        if self.app_id and self.app_secret:
            return
        self._load_feishu_env()
        self.app_id = self.app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = self.app_secret or os.getenv("FEISHU_APP_SECRET")

    def _ensure_token(self):
        """保证 token 可用"""
        if self.token:
            return self.token

        self._resolve_app_credentials()
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "缺少 FEISHU_APP_ID / FEISHU_APP_SECRET，请配置 ~/.openclaw/secrets/feishu.env"
            )

        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        response = requests.post(
            url,
            json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            },
            timeout=30,
        )
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(f"获取 tenant token 失败: {result}")

        self.token = result["tenant_access_token"]
        return self.token

    def _json_request(self, method, url, **kwargs):
        token = self._ensure_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(
                f"飞书 API 调用失败: status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}, request_id={result.get('request_id')}"
            )
        return result

    def create_document(self, title):
        """创建 docx 文档并返回 (doc_id, doc_url)。"""
        url = f"{self.base_url}/docx/v1/documents"
        result = self._json_request("POST", url, json={"title": title})
        document = result.get("data", {}).get("document", {})
        doc_id = document.get("document_id")
        if not doc_id:
            raise RuntimeError(f"创建文档后未返回 document_id: {result}")
        
        # 获取文档根块 ID（用于后续插入内容）
        root_block_id = self._get_root_block_id(doc_id)
        
        return doc_id, f"https://feishu.cn/docx/{doc_id}", root_block_id

    def _get_root_block_id(self, doc_id):
        """获取文档的根块 ID"""
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks"
        result = self._json_request("GET", url, params={"page_size": 1})
        items = result.get("data", {}).get("items", [])
        if items:
            return items[0].get("block_id")
        # 如果找不到，返回 doc_id 作为后备
        return doc_id

    def _resolve_insert_index(self, doc_id, parent_id):
        """自动追加：返回当前 parent 下末尾插入 index。"""
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"
        result = self._json_request("GET", url, params={"page_size": 500})
        items = result.get("data", {}).get("items", [])
        return len(items)
    
    def upload_image(self, image_path, image_type="message"):
        """
        上传图片到飞书
        
        Args:
            image_path: 图片文件路径
            image_type: 图片类型（当前稳定可用: message）
            
        Returns:
            image_key: 上传成功后返回的 image_key
        """
        url = f"{self.base_url}/im/v1/images"
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        size = os.path.getsize(image_path)
        if size > 10 * 1024 * 1024:
            raise ValueError(f"图片超限（>10MB）: {image_path}")

        token = self._ensure_token()

        # 读取图片
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 准备请求
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        mime_type, _ = mimetypes.guess_type(image_path)
        files = {
            'image': (Path(image_path).name, image_data, mime_type or 'application/octet-stream')
        }
        
        data = {
            'image_type': image_type
        }
        
        # 发送请求
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            image_key = result['data']['image_key']
            print(f"✅ 图片上传成功：{image_key}")
            return image_key
        else:
            print(
                f"❌ 图片上传失败：status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}, request_id={result.get('request_id')}"
            )
            return None

    def upload_docx_media(self, image_path, doc_id):
        """上传图片到 docx 素材池，返回 file_token（用于 docx 图片块 token）。"""
        url = f"{self.base_url}/drive/v1/medias/upload_all"

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        size = os.path.getsize(image_path)
        if size > 20 * 1024 * 1024:
            raise ValueError(f"图片超限（>20MB）: {image_path}")

        token = self._ensure_token()

        headers = {
            'Authorization': f'Bearer {token}',
        }

        mime_type, _ = mimetypes.guess_type(image_path)
        with open(image_path, 'rb') as f:
            files = {
                'file': (Path(image_path).name, f, mime_type or 'application/octet-stream')
            }
            data = {
                'file_name': Path(image_path).name,
                'parent_type': 'docx_image',
                'parent_node': doc_id,
                'size': str(size),
            }
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)

        result = response.json()
        if result.get('code') == 0:
            file_token = result.get('data', {}).get('file_token')
            if not file_token:
                print(f"❌ 素材上传成功但缺少 file_token：{result}")
                return None
            print(f"✅ Docx 素材上传成功：{file_token}")
            return file_token

        print(
            f"❌ Docx 素材上传失败：status={response.status_code}, code={result.get('code')}, "
            f"msg={result.get('msg')}, request_id={result.get('request_id')}"
        )
        return None
    
    def insert_image_to_docx(self, doc_id, parent_id, image_token):
        """
        插入图片到飞书文档
        
        Args:
            doc_id: 文档 ID
            parent_id: 父块 ID（可传 None，自动获取根块）
            image_token: 图片 token（推荐使用 drive media file_token）
            
        Returns:
            bool: 是否成功
        """
        token = self._ensure_token()
        
        # 自动获取根块 ID
        if parent_id is None:
            parent_id = self._get_root_block_id(doc_id)

        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # block_type 27 = image
        payload = {
            "blocks": [
                {
                    "block_type": 27,
                    "image": {
                        "file_token": image_token
                    }
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            print(f"✅ 图片插入成功")
            return True
        else:
            print(
                f"❌ 图片插入失败：status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}, request_id={result.get('request_id')}"
            )
            return False
    
    def create_table_in_docx(self, doc_id, parent_id, table_data, after_position=0):
        """
        创建表格到飞书文档
        
        Args:
            doc_id: 文档 ID
            parent_id: 父块 ID
            table_data: 表格数据 (二维数组)
            after_position: 插入位置
            
        Returns:
            bool: 是否成功
        """
        token = self._ensure_token()
        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        rows = len(table_data)
        cols = len(table_data[0]) if table_data else 0
        
        # 构建表格单元格（飞书需要每个单元格是 block 格式）
        cells = []
        for row_idx, row in enumerate(table_data):
            for col_idx, cell_text in enumerate(row):
                cells.append({
                    "row_index": row_idx,
                    "col_index": col_idx,
                    "block": {
                        "block_type": 1,
                        "text": {
                            "elements": [{
                                "text_run": {
                                    "content": str(cell_text)
                                }
                            }]
                        }
                    }
                })
        
        # 飞书 API 格式：blocks 数组
        payload = {
            "blocks": [
                {
                    "block_type": 7,
                    "table": {
                        "rows_count": rows,
                        "cols_count": cols,
                        "cells": cells
                    }
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        # 处理响应
        try:
            result = response.json()
        except:
            result = {"code": response.status_code, "msg": response.text[:200]}
        
        if result.get('code') == 0:
            print(f"✅ 表格创建成功")
            return True
        else:
            print(
                f"❌ 表格创建失败：status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}"
            )
            print(f"Payload: {payload}")
            return False

    def insert_text_to_docx(self, doc_id, text, parent_id=None, style="text"):
        """
        插入文本到飞书文档（使用 blocks API 批量插入）
        
        Args:
            doc_id: 文档 ID
            text: 文本内容
            parent_id: 父块 ID（可传 None，自动获取根块）
            style: 文本样式 ("text"|"heading1"|"heading2"|"heading3"|"bullet"|"quote")
            
        Returns:
            bool: 是否成功
        """
        token = self._ensure_token()
        
        # 自动获取根块 ID
        if parent_id is None:
            parent_id = self._get_root_block_id(doc_id)

        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # 根据样式确定 block_type
        # 飞书 API block_type: 1=文本，2=一级标题，3=二级标题，4=三级标题，5=无序列表，6=引用
        block_type_map = {
            "text": 1,
            "heading1": 2,
            "heading2": 3,
            "heading3": 4,
            "bullet": 5,
            "quote": 6,
        }
        block_type = block_type_map.get(style, 1)

        # 使用 blocks API（更稳定）
        payload = {
            "blocks": [
                {
                    "block_type": block_type,
                    "text": {
                        "elements": [
                            {
                                "text_run": {
                                    "content": text
                                }
                            }
                        ]
                    }
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()

        if result.get('code') == 0:
            print(f"✅ 文本插入成功 (样式：{style})")
            return True
        else:
            print(
                f"❌ 文本插入失败：status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}, request_id={result.get('request_id')}"
            )
            return False

    def insert_divider_to_docx(self, doc_id, parent_id=None):
        """
        插入分割线到飞书文档
        
        Args:
            doc_id: 文档 ID
            parent_id: 父块 ID（可传 None，自动获取根块）
            
        Returns:
            bool: 是否成功
        """
        token = self._ensure_token()
        
        # 自动获取根块 ID
        if parent_id is None:
            parent_id = self._get_root_block_id(doc_id)

        url = f"{self.base_url}/docx/v1/documents/{doc_id}/blocks/{parent_id}/children"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # block_type 8 = divider
        payload = {
            "blocks": [
                {
                    "block_type": 8,
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()

        if result.get('code') == 0:
            print(f"✅ 分割线插入成功")
            return True
        else:
            print(
                f"❌ 分割线插入失败：status={response.status_code}, code={result.get('code')}, "
                f"msg={result.get('msg')}, request_id={result.get('request_id')}"
            )
            return False


def test_upload():
    """测试上传功能"""
    # 自动从 ~/.openclaw/secrets/feishu.env 获取凭证
    uploader = FeishuMediaUploader()
    
    # 测试图片
    image_path = '/Users/momo/.openclaw/workspace/output/chart_market_size.png'
    image_key = uploader.upload_image(image_path)
    
    if image_key:
        print(f"测试成功！image_key: {image_key}")
    else:
        print("测试失败")


if __name__ == '__main__':
    test_upload()
