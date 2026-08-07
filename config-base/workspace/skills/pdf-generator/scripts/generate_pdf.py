#!/usr/bin/env python3
"""
PDF Generator 修复版 — 解决中文乱码问题
"""

import argparse
import os
import sys
from pathlib import Path

# 改进的 CSS，解决中文乱码
FIXED_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center { 
        content: counter(page) " / " counter(pages); 
        font-size: 9pt; 
        color: #999; 
        font-family: "Heiti SC", "STHeiti", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    }
}
body {
    font-family: "Heiti SC", "STHeiti", "Noto Sans CJK SC", "Source Han Sans CN",
                 "Microsoft YaHei", sans-serif;
    font-size: 11pt;
    line-height: 1.8;
    color: #333;
}
h1 { 
    font-size: 22pt; 
    color: #1a1a2e; 
    border-bottom: 2px solid #16213e; 
    padding-bottom: 8px; 
    margin-top: 0; 
    font-weight: 600; 
}
h2 { 
    font-size: 16pt; 
    color: #16213e; 
    margin-top: 1.5em; 
    font-weight: 600; 
}
h3 { 
    font-size: 13pt; 
    color: #0f3460; 
    font-weight: 600; 
}
table { 
    width: 100%; 
    border-collapse: collapse; 
    margin: 1em 0; 
    font-size: 10pt; 
}
th { 
    background: #16213e; 
    color: white; 
    padding: 8px 12px; 
    text-align: left; 
    font-weight: 600; 
}
td { 
    padding: 6px 12px; 
    border-bottom: 1px solid #ddd; 
}
tr:nth-child(even) { 
    background: #f8f9fa; 
}
code { 
    background: #f4f4f4; 
    padding: 2px 6px; 
    border-radius: 3px; 
    font-size: 10pt; 
    font-family: "Menlo", "Monaco", "Courier New", "Heiti SC", "STHeiti", "Noto Sans CJK SC", monospace; 
}
pre { 
    background: #f8f9fa; 
    padding: 12px; 
    border-radius: 6px; 
    overflow-x: auto; 
    font-size: 9.5pt; 
    font-family: "Menlo", "Monaco", "Courier New", "Heiti SC", "STHeiti", "Noto Sans CJK SC", monospace; 
}
blockquote { 
    border-left: 4px solid #16213e; 
    padding-left: 1em; 
    color: #555; 
    margin: 1em 0; 
    font-style: italic; 
}
.cover { 
    text-align: center; 
    padding-top: 30%; 
}
.cover h1 { 
    font-size: 28pt; 
    border: none; 
    font-weight: 700; 
}
.cover .subtitle { 
    font-size: 14pt; 
    color: #666; 
    margin-top: 1em; 
}
.cover .date { 
    font-size: 11pt; 
    color: #999; 
    margin-top: 2em; 
}
.toc { 
    page-break-after: always; 
}
.section { 
    page-break-before: always; 
}
"""

def md_to_html(md_text: str) -> str:
    """Markdown → HTML"""
    import markdown
    extensions = ["tables", "fenced_code", "codehilite", "toc", "nl2br"]
    return markdown.markdown(md_text, extensions=extensions)

def build_html(content: str, title: str = "") -> str:
    """组装完整HTML"""
    title_block = f'<div class="cover"><h1>{title}</h1></div>' if title else ""
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>{FIXED_CSS}</style>
</head>
<body>
{title_block}
{content}
</body>
</html>"""

def generate_pdf(html_content: str, output_path: str) -> dict:
    """HTML → PDF"""
    from weasyprint import HTML
    from pathlib import Path
    
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        HTML(string=html_content).write_pdf(str(out))
        return {
            "success": True,
            "path": str(out),
            "size": out.stat().st_size
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="PDF Generator 修复版")
    parser.add_argument("--input", help="输入Markdown文件")
    parser.add_argument("--output", required=True, help="输出PDF文件")
    parser.add_argument("--title", default="", help="文档标题")
    
    args = parser.parse_args()
    
    if not args.input:
        print("❌ 需要指定输入文件")
        sys.exit(1)
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 输入文件不存在: {args.input}")
        sys.exit(1)
    
    print(f"📄 读取文件: {args.input}")
    try:
        md_content = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print("❌ 文件编码错误，尝试其他编码...")
        try:
            md_content = input_path.read_text(encoding="gbk")
        except:
            print("❌ 无法解码文件")
            sys.exit(1)
    
    print("🔄 转换Markdown为HTML...")
    html_content = md_to_html(md_content)
    
    print("🎨 构建HTML文档...")
    full_html = build_html(html_content, args.title)
    
    print("📄 生成PDF...")
    result = generate_pdf(full_html, args.output)
    
    if result["success"]:
        size_kb = result["size"] / 1024
        print(f"✅ PDF已生成: {args.output} ({size_kb:.1f} KB)")
        print(f"MEDIA: {args.output}")
    else:
        print(f"❌ PDF生成失败: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()