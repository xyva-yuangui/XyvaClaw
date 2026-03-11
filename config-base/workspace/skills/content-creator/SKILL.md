---
name: content-creator
description: |
triggers: 
metadata: 
openclaw: 
emoji: "✍️"
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["content-creation", "writing"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "📝", "category": "tools", "priority": "medium"}
---

# Content Creator - 内容创作助手

内容创作助手。**触发后必须先询问用户确认**，再执行创作。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 报告创作 | 确认报告主题、深度 (快速/标准/深度)、输出格式 |
| 文章写作 | 确认文章类型、风格 (专业/休闲/创意)、字数 |
| 演示文稿 | 确认主题、页数、目标受众 |
| 文档生成 | 确认文档类型、内容来源、接收人 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行创作 → 返回文档

Full docs: read SKILL-REFERENCE.md

整合多个技能的内容创作工作流，提升创作效率 10 倍。

---

## 🎯 功能

- ✅ 深度调研（academic-deep-research）
- ✅ 人性化改写（humanize-ai-text）
- ✅ UI/图表设计（superdesign）
- ✅ 代码生成（coding）
- ✅ 文档创建（feishu-doc-extended/word-docx）

---

## 🚀 使用场景

### 1. 行业调研报告
```python
creator.create(
    topic="AI 漫剧行业分析",
    style="professional",
    template="report"
)
```

### 2. 技术博客文章
```python
creator.create(
    topic="Playwright 浏览器自动化",
    style="casual",
    template="blog"
)
```

### 3. 商业演示文稿
```python
creator.create(
    topic="Q4 投资战略",
    style="professional",
    template="presentation"
)
```

### 4. 产品文档
```python
creator.create(
    topic="产品功能说明",
    style="professional",
    template="documentation"
)
```

---

## 📋 工作流

```
1. 调研 (research)
   ↓
2. 改写 (humanize)
   ↓
3. 设计 (design)
   ↓
4. 代码 (generate_code) [可选]
   ↓
5. 文档 (create_document)
```

---

## 🔧 API 参考

### ContentCreator 类

#### 初始化
```python
creator = ContentCreator(output_dir="./output")
```

#### 调研
```python
result = creator.research(
    topic="AI 漫剧行业",
    depth="standard"  # quick/standard/deep
)
```

#### 改写
```python
content = creator.humanize(
    content=raw_content,
    style="professional"  # professional/casual/creative
)
```

#### 设计
```python
design = creator.design(
    content=content,
    template="report"  # report/presentation/blog
)
```

#### 生成代码
```python
code = creator.generate_code(
    content=content,
    language="python"  # python/javascript/bash
)
```

#### 创建文档
```python
doc_url = creator.create_document(
    content=content,
    title="我的报告",
    format="feishu"  # feishu/word/markdown
)
```

#### 完整流程
```python
result = creator.create(
    topic="AI 漫剧行业分析",
    style="professional",
    template="report",
    format="feishu"
)
```

---

## 📊 输出示例

```json
{
    "topic": "AI 漫剧行业分析",
    "style": "professional",
    "template": "report",
    "format": "feishu",
    "document": "https://feishu.cn/docx/xxx",
    "charts": [
        {"type": "bar", "title": "市场规模", "file": "chart1.png"},
        {"type": "pie", "title": "用户分布", "file": "chart2.png"}
    ],
    "research": {
        "sources": ["36 氪", "DataEye", "浙商证券"],
        "key_points": ["市场规模 200 亿", "增长 45%"],
        "data": {"market_size": "200 亿元"}
    }
}
```

---

## 💡 最佳实践

### 1. 选择合适的风格
- **professional**：报告/论文/商业文档
- **casual**：博客/社交媒体/内部沟通
- **creative**：营销文案/创意内容

### 2. 选择正确的模板
- **report**：调研报告/分析报告
- **presentation**：演示文稿/PPT
- **blog**：博客文章/公众号
- **documentation**：技术文档/产品说明

### 3. 优化调研深度
- **quick**：快速了解（5 分钟）
- **standard**：标准调研（30 分钟）
- **deep**：深度调研（2 小时）

---

## 🎨 示例输出

### 行业调研报告
```markdown
# AI 漫剧行业深度调研报告

## 核心结论
1. 市场规模：200 亿 → 243 亿（+45%）
2. 用户群体：1.2 亿活跃用户
3. 竞争格局：字节、腾讯、快手主导

## 市场规模
[图表：柱状图]

## 用户画像
[图表：饼图]

## 结论建议
...
```

---

## 📁 文件结构

```
content-creator/
├── SKILL.md              # 技能定义
├── content_creator.py    # 主程序
├── templates/            # 文档模板
│   ├── report.md
│   ├── presentation.md
│   └── blog.md
└── output/               # 输出目录
    ├── research_*.json   # 调研结果
    ├── chart_*.png       # 图表
    └── doc_*.md          # 文档
```

---

## 🚀 快速开始

```bash
cd ~/.openclaw/workspace/skills/content-creator
python3 content_creator.py
```

---

## 📞 支持

遇到问题请查看：
- [SKILL-COMBINATION-ANALYSIS.md](../SKILL-COMBINATION-ANALYSIS.md) - 技能组合分析
- [AUTO-INSTALL-SETUP.md](../AUTO-INSTALL-SETUP.md) - 自动安装配置

---

**版本**：1.0.0  
**创建时间**：2026-03-03  
**依赖技能**：academic-deep-research, humanize-ai-text, superdesign, coding, feishu-doc-extended
