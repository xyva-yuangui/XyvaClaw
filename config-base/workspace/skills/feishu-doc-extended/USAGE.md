# 🚀 自动化报告生成系统 - 使用指南

---

## 📋 概述

这是一个完全自动化的飞书文档报告生成系统，可以：

1. ✅ 自动生成数据图表
2. ✅ 创建飞书文档（文字内容）
3. ✅ 发送图表到群聊
4. ✅ 提供完整汇报材料

---

## 🎯 快速开始

### 方法 1：一键生成（推荐）

```bash
cd ~/.openclaw/workspace/skills/feishu-doc-extended
python3 quick_report.py
```

**输出**：
- 4 张数据图表
- 飞书文档链接
- 使用指南

### 方法 2：在 OpenClaw 中使用

在对话中说：
```
生成 AI 漫剧行业调研报告
```

系统会自动：
1. 生成图表
2. 创建文档
3. 发送到群聊

---

## 📊 生成的内容

### 1. 数据图表（4 张）

| 文件名 | 内容 | 用途 |
|--------|------|------|
| `chart_market_size.png` | 市场规模对比 | 展示增长趋势 |
| `chart_age_distribution.png` | 年龄分布饼图 | 展示用户结构 |
| `chart_revenue_model.png` | 变现模式占比 | 展示商业模式 |
| `chart_cost_comparison.png` | 成本对比柱状图 | 展示成本优势 |

### 2. 飞书文档

**包含内容**：
- ✅ 核心结论
- ✅ 市场概况
- ✅ 用户画像
- ✅ 竞争格局
- ✅ 商业模式
- ✅ 技术进展
- ✅ 政策法规
- ✅ 海外市场
- ✅ 投资建议
- ✅ 结论建议

**文档特点**：
- 📝 结构化排版
- 📊 图表位置标注
- 🎯 适合汇报演示

---

## 🔧 自定义报告

### 修改图表

编辑图表生成脚本：
```bash
vim /Users/momo/.openclaw/workspace/output/generate_charts.py
```

可以：
- 修改图表类型
- 调整颜色样式
- 添加新的图表

### 修改文档内容

使用 `feishu_doc` 工具：
```json
{
  "action": "write",
  "doc_token": "YOUR_DOC_TOKEN",
  "content": "# 你的报告内容"
}
```

---

## 📁 文件结构

```
~/.openclaw/workspace/skills/feishu-doc-extended/
├── SKILL.md              # 技能定义
├── README.md             # 项目说明
├── USAGE.md              # 使用指南（本文件）
├── feishu_media_upload.py  # 图片上传模块
├── auto_report_generator.py  # 完整自动化脚本
├── quick_report.py       # 快速生成脚本
└── generate_ai_manju_report.py  # AI 漫剧报告专用

/Users/momo/.openclaw/workspace/output/
├── generate_charts.py    # 图表生成脚本
├── chart_market_size.png  # 市场规模图
├── chart_age_distribution.png  # 年龄分布图
├── chart_revenue_model.png  # 变现模式图
└── chart_cost_comparison.png  # 成本对比图
```

---

## 💡 最佳实践

### 汇报流程

**步骤 1**：生成报告
```bash
python3 quick_report.py
```

**步骤 2**：打开飞书文档
- 查看完整文字内容
- 熟悉报告结构

**步骤 3**：查看群聊图表
- 4 张数据图表
- 对应文档中的 📊 标注

**步骤 4**：开始汇报
- 投屏飞书文档
- 对照图表讲解数据
- 使用结论建议部分

### 报告优化

**添加更多图表**：
1. 编辑 `generate_charts.py`
2. 添加新的 `plot_*()` 函数
3. 更新 `quick_report.py` 中的图表列表

**自定义文档模板**：
1. 创建 Markdown 模板文件
2. 使用 `feishu_doc` 的 `write` 操作
3. 保存为模板供下次使用

---

## ⚠️ 注意事项

### 图表生成

- 需要安装 `matplotlib`
- 中文字体可能需要配置
- 图表大小默认 10x6 英寸

### 飞书文档

- 文档图片插入使用 `im/v1/images` + `docx/v1/documents/{doc_id}/blocks`
- 上传图片务必使用 `image_type=docx`
- 文档权限需要配置并在飞书后台发布生效

### 性能

- 图表生成：约 2-3 秒
- 文档创建：约 1-2 秒
- 图片上传：约 1-2 秒/张
- 总计：约 10 秒完成

---

## 🐛 故障排除

### 图表生成失败

**错误**：`ModuleNotFoundError: No module named 'matplotlib'`

**解决**：
```bash
pip3 install matplotlib
```

### 文档创建失败

**错误**：`Request failed with status code 400`

**解决**：
- 检查飞书权限配置
- 确认文档 token 正确
- 内容不要太长（分块写入）

### 图片无法显示

**错误**：图片路径不存在

**解决**：
- 检查图表是否已生成
- 确认路径正确
- 重新运行生成脚本

---

## 📞 技术支持

遇到问题请查看：

1. [README.md](README.md) - 项目说明
2. [SKILL.md](SKILL.md) - 技能定义
3. [飞书开放平台文档](https://open.feishu.cn/document/)
4. [OpenClaw 文档](https://docs.openclaw.ai)

---

## 🎉 示例输出

运行 `python3 quick_report.py` 后：

```
============================================================
🤖 快速报告生成器
============================================================
📊 生成图表...
✅ 图表生成完成
📄 创建文档...

============================================================
✅ 报告生成完成！
============================================================

📄 文档链接：https://feishu.cn/docx/TF02dzfAyoJtyUxbAUUcyfZbnGb

📊 图表文件：4 张
  - chart_market_size.png
  - chart_age_distribution.png
  - chart_revenue_model.png
  - chart_cost_comparison.png

📋 下一步：
1. 打开飞书文档查看文字内容
2. 查看群聊中的图表
3. 对照文档中的 📊 标注查看对应图表
```

---

**版本**：1.0.0  
**更新时间**：2026-03-03  
**开发者**：OpenClaw + 飞书集成
