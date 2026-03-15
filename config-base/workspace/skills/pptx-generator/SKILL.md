---
name: pptx-generator
description: 生成 PowerPoint (PPTX) 演示文稿。支持创建多页幻灯片、标题页、内容页、图片页、表格页、图表页。用户需要制作 PPT/演示文稿时使用此技能。
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-15
provides: ["pptx_generator"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "📊", "category": "tools", "priority": "medium"}
---

# PPTX Generator

生成专业的 PowerPoint 演示文稿。

## 功能

- **标题页**：大标题 + 副标题
- **内容页**：标题 + 多级要点列表
- **图片页**：标题 + 图片（本地路径或 URL）
- **表格页**：标题 + 数据表格
- **双栏页**：左右分栏布局
- **空白页**：自由定位元素

## 使用方式

```bash
# 健康检查
python3 scripts/check.py

# 从 JSON 描述生成 PPT
python3 scripts/pptx_tool.py generate --input slides.json --output presentation.pptx

# 从 Markdown 生成 PPT（每个 ## 标题成为一页）
python3 scripts/pptx_tool.py from-markdown --input content.md --output presentation.pptx

# 添加单页到已有 PPT
python3 scripts/pptx_tool.py add-slide --file existing.pptx --title "新页面" --content "内容"
```

## JSON 格式

```json
{
  "title": "演示文稿标题",
  "author": "作者",
  "slides": [
    {
      "layout": "title",
      "title": "欢迎",
      "subtitle": "副标题"
    },
    {
      "layout": "content",
      "title": "要点",
      "bullets": ["第一点", "第二点", "第三点"]
    },
    {
      "layout": "table",
      "title": "数据对比",
      "headers": ["指标", "A方案", "B方案"],
      "rows": [["性能", "95%", "88%"], ["成本", "低", "高"]]
    }
  ]
}
```

## 输出目录

`$OPENCLAW_HOME/workspace/output/pptx/`

## 依赖

- python-pptx (`pip3 install python-pptx`)
