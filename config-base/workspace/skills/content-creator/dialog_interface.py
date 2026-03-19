#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容创作助手 - 对话接口
支持自然语言对话，自动识别创作需求
"""

import re
import json
from pathlib import Path
from datetime import datetime
from content_creator import ContentCreator
from publisher import ContentPublisher

class DialogInterface:
    """对话式内容创作接口"""
    
    def __init__(self):
        """初始化对话接口"""
        self.creator = ContentCreator()
        self.publisher = ContentPublisher()
        
        # 发布意图关键词
        self.publish_patterns = {
            'xhs': ['小红书', 'xhs', '红书'],
            'feishu': ['飞书', 'docx', '文档'],
            'wechat': ['微信', '公众号', '朋友圈']
        }
        
        # 意图识别关键词
        self.intent_patterns = {
            'create_report': [
                r'写.*报告',
                r'生成.*报告',
                r'创作.*报告',
                r'调研.*报告',
                r'分析.*行业',
                r'行业.*分析'
            ],
            'create_blog': [
                r'写.*文章',
                r'写.*博客',
                r'公众号.*文章',
                r'技术.*文章'
            ],
            'create_presentation': [
                r'演示.*文稿',
                r'PPT',
                r'演示.*汇报',
                r'商业.*计划'
            ],
            'create_documentation': [
                r'产品.*文档',
                r'功能.*说明',
                r'技术.*文档',
                r'使用.*手册'
            ]
        }
        
        # 风格识别
        self.style_map = {
            'professional': ['专业', '正式', '商业', '报告', '论文'],
            'casual': ['轻松', '随意', '博客', '公众号', '日常'],
            'creative': ['创意', '营销', '广告', '文案', '有趣']
        }
        
        # 模板识别
        self.template_map = {
            'report': ['报告', '调研', '分析', '研究'],
            'blog': ['文章', '博客', '公众号', '推文'],
            'presentation': ['演示', 'PPT', '汇报', '演讲'],
            'documentation': ['文档', '说明', '手册', '指南']
        }
    
    def detect_publish_platform(self, text: str) -> str:
        """
        识别发布平台
        
        Args:
            text: 用户输入
            
        Returns:
            str: 平台类型 (xhs/feishu/wechat/none)
        """
        text_lower = text.lower()
        
        # 检查是否包含发布相关词汇
        if not any(word in text_lower for word in ['发布', '发表', '推送', 'post', 'share']):
            return 'none'
        
        # 识别平台
        for platform, keywords in self.publish_patterns.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return platform
        
        return 'xhs'  # 默认小红书
    
    def detect_intent(self, text: str) -> str:
        """
        识别用户意图
        
        Args:
            text: 用户输入
            
        Returns:
            str: 意图类型
        """
        text_lower = text.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent
        
        return 'general'
    
    def detect_style(self, text: str) -> str:
        """
        识别写作风格
        
        Args:
            text: 用户输入
            
        Returns:
            str: 风格类型
        """
        text_lower = text.lower()
        
        for style, keywords in self.style_map.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return style
        
        # 默认根据意图推断
        intent = self.detect_intent(text)
        if intent == 'create_report':
            return 'professional'
        elif intent == 'create_blog':
            return 'casual'
        elif intent == 'create_presentation':
            return 'professional'
        else:
            return 'professional'
    
    def detect_template(self, text: str) -> str:
        """
        识别文档模板
        
        Args:
            text: 用户输入
            
        Returns:
            str: 模板类型
        """
        text_lower = text.lower()
        
        for template, keywords in self.template_map.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return template
        
        # 默认根据意图推断
        intent = self.detect_intent(text)
        template_map = {
            'create_report': 'report',
            'create_blog': 'blog',
            'create_presentation': 'presentation',
            'create_documentation': 'documentation'
        }
        return template_map.get(intent, 'report')
    
    def extract_topic(self, text: str) -> str:
        """
        提取创作主题
        
        Args:
            text: 用户输入
            
        Returns:
            str: 主题
        """
        # 尝试提取引号内的内容
        match = re.search(r'[""](.*?)[""]', text)
        if match:
            return match.group(1)
        
        # 尝试提取"关于"后面的内容
        match = re.search(r'关于 (.+?)(?:的 | 吗 | ？|$)', text)
        if match:
            return match.group(1).strip()
        
        # 尝试提取动词后面的内容
        verbs = ['写', '生成', '创作', '调研', '分析']
        for verb in verbs:
            match = re.search(rf'{verb}(.+?)(?:的 | 吗 | ？|$)', text)
            if match:
                topic = match.group(1).strip()
                # 去除模板词
                for template in ['报告', '文章', '博客', '文档', 'PPT']:
                    topic = topic.replace(template, '')
                return topic.strip()
        
        # 默认返回整个句子
        return text[:50]
    
    def process(self, user_input: str) -> dict:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            
        Returns:
            dict: 处理结果
        """
        print("\n" + "=" * 60)
        print("🤖 内容创作助手 - 对话模式")
        print("=" * 60)
        
        # 1. 识别意图
        intent = self.detect_intent(user_input)
        print(f"\n📋 识别意图：{intent}")
        
        # 2. 识别风格
        style = self.detect_style(user_input)
        print(f"🎨 识别风格：{style}")
        
        # 3. 识别模板
        template = self.detect_template(user_input)
        print(f"📄 识别模板：{template}")
        
        # 4. 提取主题
        topic = self.extract_topic(user_input)
        print(f"🎯 提取主题：{topic}")
        
        # 5. 识别发布平台
        publish_platform = self.detect_publish_platform(user_input)
        auto_publish = publish_platform != 'none'
        print(f"📱 发布平台：{publish_platform if auto_publish else '暂不发布'}")
        
        # 6. 确认参数
        print(f"\n✅ 确认创作参数:")
        print(f"   主题：{topic}")
        print(f"   风格：{style}")
        print(f"   模板：{template}")
        if auto_publish:
            print(f"   发布：{publish_platform}")
        
        # 7. 执行创作
        print(f"\n🚀 开始创作...")
        
        result = self.creator.create(
            topic=topic,
            style=style,
            template=template,
            format="feishu"
        )
        
        # 8. 发布（如果需要）
        if auto_publish:
            print(f"\n📱 准备发布到 {publish_platform}...")
            
            # 准备发布内容
            publish_content = {
                'topic': topic,
                'key_points': result['research'].get('key_points', []),
                'document': result['document']
            }
            
            # 执行发布
            publish_result = self.publisher.publish(
                publish_content,
                platform=publish_platform,
                auto=True
            )
            
            result['publish'] = publish_result
        
        # 9. 返回结果
        print(f"\n✅ 创作完成！")
        print(f"📄 文档链接：{result['document']}")
        print(f"🎨 图表数量：{len(result['charts'])} 个")
        if auto_publish and 'publish' in result:
            print(f"📱 发布状态：{result['publish'].get('message', '已准备素材')}")
        
        return {
            'success': True,
            'intent': intent,
            'topic': topic,
            'style': style,
            'template': template,
            'document': result['document'],
            'charts': len(result['charts']),
            'publish': publish_platform if auto_publish else 'none',
            'message': f"✅ 已完成《{topic}》创作" + (f"并发布到{publish_platform}" if auto_publish else "")
        }
    
    def chat(self, user_input: str) -> str:
        """
        对话接口（返回文本）
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 回复文本
        """
        try:
            result = self.process(user_input)
            
            if result['success']:
                # 生成友好的回复
                response = f"""
✅ **内容创作完成！**

📄 **文档链接**：{result['document']}

📊 **创作详情**：
- 主题：{result['topic']}
- 风格：{result['style']}
- 模板：{result['template']}
- 图表：{result['charts']} 个
"""
                
                if result.get('publish') != 'none':
                    platform_name = {
                        'xhs': '小红书',
                        'feishu': '飞书',
                        'wechat': '微信公众号'
                    }.get(result['publish'], result['publish'])
                    
                    response += f"""
📱 **发布状态**：已发布到 {platform_name}
"""
                
                response += f"""
💡 **下一步**：
1. 点击文档链接查看完整内容
2. 如需修改风格或模板，请告诉我
3. 可以继续创作其他主题

需要我继续创作其他内容吗？😊
"""
                return response
            else:
                return "❌ 创作失败，请稍后重试"
                
        except Exception as e:
            print(f"❌ 错误：{e}")
            return f"❌ 创作过程中出现错误：{str(e)}\n请稍后重试或联系管理员"


def main():
    """测试对话接口"""
    dialog = DialogInterface()
    
    # 测试用例
    test_cases = [
        "帮我写一篇关于 AI 漫剧行业分析的报告",
        "创作一篇轻松风格的技术博客，关于 Playwright 浏览器自动化",
        "生成一份 Q4 投资战略的商业演示文稿",
        "写一份产品功能说明文档"
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"🗣️  用户：{test}")
        print(f"{'='*60}")
        
        response = dialog.chat(test)
        print(f"\n🤖 助手：{response}")
        
        print("\n\n")


if __name__ == '__main__':
    main()
