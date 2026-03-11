#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速报告生成器 - 调用可执行的飞书文档+图片流水线

流程：
1. 生成图表
2. 创建飞书文档
3. 上传图片（docx）
4. 插入图片到文档
"""

import subprocess
import sys

def main():
    """主函数"""
    print("=" * 60)
    print("🤖 快速报告生成器")
    print("=" * 60)
    
    result = subprocess.run(
        [
            sys.executable,
            '/Users/momo/.openclaw/workspace/skills/feishu-doc-extended/generate_ai_manju_report.py',
        ]
    )
    return result.returncode == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
