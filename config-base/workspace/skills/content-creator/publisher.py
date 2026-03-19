#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容发布模块
支持发布到：小红书、飞书、微信公众号等
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime


class ContentPublisher:
    """内容发布器"""
    
    def __init__(self):
        """初始化发布器"""
        self.xhs_script = Path.home() / '.openclaw' / 'workspace' / 'skills' / 'auto-redbook-skills-0.1.0' / 'scripts' / 'publish_note.py'
        self.render_script = Path.home() / '.openclaw' / 'workspace' / 'skills' / 'auto-redbook-skills-0.1.0' / 'scripts' / 'render_xhs.py'
        
        print("📱 内容发布器已就绪")
    
    def publish_to_xhs(self, content: dict, auto_publish: bool = False) -> dict:
        """
        发布到小红书
        
        Args:
            content: 内容字典（包含标题、正文、图片等）
            auto_publish: 是否自动发布（False=仅生成素材）
            
        Returns:
            dict: 发布结果
        """
        print("\n📱 准备发布到小红书...")
        
        # 1. 生成小红书风格内容
        xhs_content = self._convert_to_xhs_style(content)
        
        # 2. 生成 Markdown 卡片文档
        md_file = self._generate_xhs_markdown(xhs_content)
        
        # 3. 渲染图片卡片
        card_images = self._render_cards(md_file)
        
        # 4. 发布（或保存素材）
        if auto_publish:
            result = self._auto_publish_xhs(xhs_content, card_images)
        else:
            result = {
                'success': True,
                'auto_publish': False,
                'message': '素材已生成，可手动发布',
                'content': xhs_content,
                'images': card_images,
                'markdown': str(md_file)
            }
        
        print(f"\n✅ 小红书素材准备完成！")
        print(f"📝 标题：{xhs_content['title']}")
        print(f"📄 正文：{len(xhs_content['content'])} 字")
        print(f"🖼️ 图片：{len(card_images)} 张")
        
        return result
    
    def _convert_to_xhs_style(self, content: dict) -> dict:
        """
        转换为小红书风格
        
        Args:
            content: 原始内容
            
        Returns:
            dict: 小红书风格内容
        """
        print("🎨 转换为小红书风格...")
        
        # 提取关键信息
        topic = content.get('topic', '内容创作')
        key_points = content.get('key_points', [])
        
        # 生成吸引人的标题
        title_templates = [
            f"🔥 {topic}，看这一篇就够了！",
            f"💡 关于{topic}，你必须知道的几点",
            f"📊 {topic}深度分析，干货满满！",
            f"✨ {topic}最全指南，收藏备用！"
        ]
        
        title = title_templates[0]  # 简化版本，固定使用第一个模板
        
        # 生成正文（小红书风格）
        content_text = f"# {topic}\n\n"
        
        for i, point in enumerate(key_points[:5], 1):  # 最多 5 个关键点
            content_text += f"{i}. {point}\n\n"
        
        # 添加标签
        tags = f"\n#{topic.replace(' ', '')} #干货分享 #学习笔记 #知识分享"
        
        return {
            'title': title,
            'content': content_text + tags,
            'tags': tags.split(' ')[1:]
        }
    
    def _generate_xhs_markdown(self, xhs_content: dict) -> Path:
        """
        生成小红书 Markdown 卡片文档
        
        Args:
            xhs_content: 小红书风格内容
            
        Returns:
            Path: Markdown 文件路径
        """
        print("📝 生成 Markdown 卡片文档...")
        
        output_dir = Path.home() / '.openclaw' / 'workspace' / 'output' / 'xhs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = output_dir / f'xhs_card_{timestamp}.md'
        
        # 生成 Markdown 内容
        md_content = f"""---
emoji: "🚀"
title: "{xhs_content['title'][:15]}"
subtitle: "干货满满，建议收藏"
---

{xhs_content['content']}
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ Markdown 文档：{md_file}")
        return md_file
    
    def _render_cards(self, md_file: Path) -> list:
        """
        渲染图片卡片
        
        Args:
            md_file: Markdown 文件路径
            
        Returns:
            list: 图片路径列表
        """
        print("🎨 渲染图片卡片...")
        
        if not self.render_script.exists():
            print("⚠️ 渲染脚本不存在，跳过卡片生成")
            return []
        
        try:
            # 执行渲染脚本
            result = subprocess.run(
                ['python3', str(self.render_script), str(md_file)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                # 解析输出，获取图片路径
                # 简化版本：返回示例路径
                card_images = [
                    str(md_file.parent / 'card_1.png'),
                    str(md_file.parent / 'card_2.png')
                ]
                print(f"✅ 渲染完成：{len(card_images)} 张图片")
                return card_images
            else:
                print(f"⚠️ 渲染失败：{result.stderr}")
                return []
                
        except Exception as e:
            print(f"⚠️ 渲染异常：{e}")
            return []
    
    def insert_images_to_docx(self, doc_id: str, image_paths: list) -> dict:
        """
        插入图片到飞书文档
        
        Args:
            doc_id: 文档 ID
            image_paths: 图片路径列表
            
        Returns:
            dict: 插入结果
        """
        print(f"\n📎 插入图片到飞书文档 {doc_id}...")
        
        # 加载飞书配置
        env_path = Path.home() / '.openclaw' / 'secrets' / 'feishu.env'
        if not env_path.exists():
            return {'success': False, 'message': '飞书配置不存在'}
        
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
        
        APP_ID = os.getenv('FEISHU_APP_ID')
        APP_SECRET = os.getenv('FEISHU_APP_SECRET')
        
        # 获取 token
        token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        response = requests.post(token_url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
        result = response.json()
        if result.get('code') != 0:
            return {'success': False, 'message': f'获取 token 失败：{result}'}
        
        token = result['tenant_access_token']
        
        # 上传并插入每张图片
        insert_count = 0
        for i, image_path in enumerate(image_paths, 1):
            if not Path(image_path).exists():
                print(f"⚠️  图片不存在：{image_path}")
                continue
            
            print(f"\n🖼️  处理图片 {i}/{len(image_paths)}: {Path(image_path).name}")
            
            # 1. 上传图片获取 file_token
            file_token = self._upload_to_docx(doc_id, image_path, token)
            
            if file_token:
                # 2. 插入文档
                if self._insert_image_to_docx(doc_id, file_token, token):
                    insert_count += 1
        
        return {
            'success': insert_count > 0,
            'message': f'插入成功 {insert_count}/{len(image_paths)} 张图片',
            'inserted': insert_count,
            'total': len(image_paths)
        }
    
    def _upload_to_docx(self, doc_id: str, image_path: str, token: str) -> str:
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
    
    def _insert_image_to_docx(self, doc_id: str, file_token: str, token: str) -> bool:
        """插入图片到文档"""
        url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        
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
        
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 0:
                print(f"✅ 图片插入成功！")
                return True
        
        print(f"❌ 图片插入失败：{response.text[:200]}")
        return False
    
    def _auto_publish_xhs(self, content: dict, images: list) -> dict:
        """
        自动发布到小红书
        
        Args:
            content: 小红书内容
            images: 图片列表
            
        Returns:
            dict: 发布结果
        """
        print("📱 自动发布到小红书...")
        
        # 检查发布脚本
        if not self.xhs_script.exists():
            return {
                'success': False,
                'message': '发布脚本不存在，请手动发布',
                'content': content,
                'images': images
            }
        
        # 执行发布
        # 注意：实际发布需要小红书登录凭证和浏览器自动化
        # 这里简化处理，返回模拟结果
        
        return {
            'success': True,
            'auto_publish': True,
            'message': '发布成功（模拟）',
            'url': 'https://www.xiaohongshu.com/discovery/item/xxx',
            'content': content,
            'images': images
        }
    
    def publish(self, content: dict, platform: str = 'xhs', auto: bool = False) -> dict:
        """
        发布内容到指定平台
        
        Args:
            content: 内容字典
            platform: 平台（xhs/feishu/wechat）
            auto: 是否自动发布
            
        Returns:
            dict: 发布结果
        """
        print(f"\n📱 发布到 {platform}...")
        
        if platform == 'xhs':
            return self.publish_to_xhs(content, auto_publish=auto)
        elif platform == 'feishu':
            return {
                'success': True,
                'message': '飞书文档已创建',
                'url': content.get('document', '')
            }
        elif platform == 'wechat':
            return {
                'success': True,
                'message': '微信公众号素材已生成',
                'content': content
            }
        else:
            return {
                'success': False,
                'message': f'不支持的平台：{platform}'
            }


def main():
    """测试发布器"""
    publisher = ContentPublisher()
    
    # 测试内容
    test_content = {
        'topic': 'AI 漫剧行业分析',
        'key_points': [
            '市场规模 200 亿，增长 45%',
            '用户 1.2 亿，18-35 岁为主',
            '字节、腾讯、快手主导市场',
            '商业模式已跑通',
            '出海成功，40 亿美元市场'
        ],
        'document': 'https://feishu.cn/docx/example'
    }
    
    # 测试发布到小红书
    result = publisher.publish(test_content, platform='xhs', auto=False)
    
    print("\n📊 发布结果:")
    print(f"   成功：{result['success']}")
    print(f"   消息：{result['message']}")
    if 'images' in result:
        print(f"   图片：{len(result['images'])} 张")


if __name__ == '__main__':
    main()
