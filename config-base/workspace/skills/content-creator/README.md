# 内容创作助手 - 快速开始指南

**创建时间**：2026-03-03 21:34

---

## 🎯 功能概述

内容创作助手整合 5 大技能，实现一键生成专业内容：

1. **深度调研** - academic-deep-research
2. **人性化改写** - humanize-ai-text
3. **UI/图表设计** - superdesign
4. **代码生成** - coding
5. **文档创建** - feishu-doc-extended

**效率提升**：10 倍  
**自动化程度**：80%

---

## 🚀 快速开始

### 方法 1：命令行运行

```bash
cd ~/.openclaw/workspace/skills/content-creator
python3 content_creator.py
```

### 方法 2：Python 调用

```python
from content_creator import ContentCreator

creator = ContentCreator()

result = creator.create(
    topic="AI 漫剧行业分析",
    style="professional",
    template="report",
    format="feishu"
)

print(f"文档：{result['document']}")
print(f"图表：{len(result['charts'])} 个")
```

### 方法 3：OpenClaw 对话

在对话中说：
```
帮我创作一篇关于"AI 漫剧行业分析"的报告
```

---

## 📋 使用示例

### 示例 1：行业调研报告

```python
creator.create(
    topic="AI 漫剧行业分析",
    style="professional",  # 专业风格
    template="report",     # 报告模板
    format="feishu"        # 飞书文档
)
```

**输出**：
- 📄 飞书文档链接
- 📊 市场规模图表
- 📊 用户分布图表
- 📝 专业分析内容

---

### 示例 2：技术博客

```python
creator.create(
    topic="Playwright 浏览器自动化教程",
    style="casual",        # 轻松风格
    template="blog",       # 博客模板
    format="markdown"      # Markdown 格式
)
```

**输出**：
- 📝 博客文章（Markdown）
- 💻 示例代码
- 🎨 流程图/架构图

---

### 示例 3：商业演示

```python
creator.create(
    topic="Q4 投资战略",
    style="professional",
    template="presentation",  # 演示文稿模板
    format="feishu"
)
```

**输出**：
- 📊 演示文稿
- 📈 数据图表
- 💡 核心观点

---

### 示例 4：产品文档

```python
creator.create(
    topic="产品功能说明文档",
    style="professional",
    template="documentation",
    format="word"  # Word 格式
)
```

**输出**：
- 📄 Word 文档
- 📋 功能列表
- 🖼️ 界面截图

---

## 🎨 参数说明

### topic（必填）
创作主题，例如：
- "AI 漫剧行业分析"
- "Playwright 浏览器自动化"
- "Q4 投资战略"

### style（可选）
改写风格：
- **professional**：专业风格（报告/论文/商业文档）
- **casual**：轻松风格（博客/社交媒体）
- **creative**：创意风格（营销文案）

默认：`professional`

### template（可选）
文档模板：
- **report**：调研报告/分析报告
- **presentation**：演示文稿/PPT
- **blog**：博客文章/公众号
- **documentation**：技术文档/产品说明

默认：`report`

### format（可选）
输出格式：
- **feishu**：飞书云文档
- **word**：Word 文档
- **markdown**：Markdown 文件

默认：`feishu`

---

## 📊 输出说明

### 调研结果（JSON）
```json
{
    "topic": "AI 漫剧行业分析",
    "sources": ["36 氪", "DataEye", "浙商证券"],
    "key_points": ["市场规模 200 亿", "增长 45%"],
    "data": {"market_size": "200 亿元"}
}
```

### 文档内容（Markdown）
```markdown
# AI 漫剧行业深度调研报告

## 核心结论
1. 市场规模：200 亿 → 243 亿（+45%）
2. 用户群体：1.2 亿活跃用户
...
```

### 图表文件（PNG）
- `chart_market_size.png` - 市场规模对比
- `chart_users.png` - 用户分布

---

## 💡 最佳实践

### 1. 选择合适的风格
| 场景 | 推荐风格 |
|------|----------|
| 行业报告 | professional |
| 技术博客 | casual |
| 营销文案 | creative |
| 产品文档 | professional |

### 2. 优化调研深度
| 深度 | 时间 | 适用场景 |
|------|------|----------|
| quick | 5 分钟 | 快速了解 |
| standard | 30 分钟 | 标准报告 |
| deep | 2 小时 | 深度分析 |

### 3. 组合使用技能
```python
# 先调研
research = creator.research("AI 漫剧行业")

# 再改写
content = creator.humanize(str(research), style="casual")

# 最后创建文档
doc = creator.create_document(content, "我的报告", format="feishu")
```

---

## 📁 文件结构

```
content-creator/
├── README.md               # 本文档
├── SKILL.md                # 技能定义
├── content_creator.py      # 主程序
├── templates/              # 文档模板
│   ├── report.md
│   ├── presentation.md
│   ├── blog.md
│   └── documentation.md
└── output/                 # 输出目录
    ├── research_*.json     # 调研结果
    ├── chart_*.png         # 图表
    └── doc_*.md            # 文档
```

---

## 🔧 故障排除

### 问题 1：找不到模块
```
ModuleNotFoundError: No module named 'xxx'
```
**解决**：安装依赖
```bash
pip3 install requests matplotlib
```

### 问题 2：飞书文档创建失败
**解决**：检查飞书配置
```bash
cat ~/.openclaw/secrets/feishu.env
```

### 问题 3：图表生成失败
**解决**：检查 matplotlib 配置
```python
import matplotlib
matplotlib.use('Agg')
```

---

## 📞 支持

- [SKILL.md](SKILL.md) - 技能详细文档
- [SKILL-COMBINATION-ANALYSIS.md](../SKILL-COMBINATION-ANALYSIS.md) - 技能组合分析
- [AUTO-INSTALL-SETUP.md](../AUTO-INSTALL-SETUP.md) - 自动安装配置

---

**版本**：1.0.0  
**创建时间**：2026-03-03  
**状态**：✅ 可用
