---
name: feishu-doc-extended
version: 1.1.0
description: |
triggers: 
metadata: 
openclaw: 
emoji: "📄"
status: stable
platform: [darwin, linux]
dependencies: 
bins: [python3]
updated: 2026-03-11
provides: ["feishu_doc_extended"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Feishu Document Tool - Extended

飞书文档助手。**触发后必须先询问用户确认**，再执行操作。

| 触发场景 | 询问确认内容 |
|----------|-------------|
| 创建文档 | 确认文档标题、内容来源、接收人 |
| 上传图片 | 确认图片路径、目标文档、插入位置 |
| 生成报告 | 确认报告主题、图表来源、文档结构 |
| 创建表格 | 确认表格数据、行列数、目标文档 |

**执行流程**: 触发 → 询问用户 → 用户确认 → 执行操作 → 返回文档链接

Full docs: read SKILL-REFERENCE.md

> 已合并 feishu-image-uploader 的全部功能

扩展功能：
- ✅ 上传图片到文档（单张/批量）
- ✅ 插入图片到指定位置
- ✅ 自动压缩（可选）、格式转换（JPG/PNG/WEBP）
- ✅ 创建表格
- ✅ 支持自动化报告脚本（生成图表 → 创建文档 → 插入图片）

## Token 获取

从飞书配置自动获取 tenant access token。

## 新增 Actions

### Upload Image (上传图片)

```json
{
  "action": "upload_image",
  "file_path": "/path/to/image.png",
  "image_type": "docx"
}
```

返回：
```json
{
  "image_key": "imgcnXXXXXXXXXX",
  "success": true
}
```

### Insert Image (插入图片)

```json
{
  "action": "insert_image",
  "doc_token": "ABC123def",
  "parent_id": "doxcnXXX",
  "image_key": "imgcnXXX",
  "after_position": 0
}
```

### Create Table (创建表格)

```json
{
  "action": "create_table",
  "doc_token": "ABC123def",
  "parent_id": "doxcnXXX",
  "table_data": [
    ["表头 1", "表头 2"],
    ["数据 1", "数据 2"],
    ["数据 3", "数据 4"]
  ],
  "after_position": 0
}
```

## 完整工作流

### 生成带图表的报告

```json
{
  "action": "generate_report",
  "title": "📊 行业调研报告",
  "content": "# Title\n\n![](/path/to/chart1.png)\n\n## Section\n\n![](/path/to/chart2.png)",
  "chart_files": [
    "/path/to/chart1.png",
    "/path/to/chart2.png"
  ]
}
```

流程：
1. 创建文档
2. 上传所有图片
3. 插入图片块到文档
4. 返回文档链接

## 当前推荐入口

```bash
cd ~/.openclaw/workspace/skills/feishu-doc-extended
python3 generate_ai_manju_report.py
```

## 配置

```yaml
channels:
  feishu:
    tools:
      doc_extended: true  # 启用扩展版
      auto_upload_images: true  # 自动上传图片
```

## Python API（原 feishu-image-uploader）

```python
from feishu_image_uploader import FeishuImageUploader

uploader = FeishuImageUploader()

# 上传单张图片 → 获取 image_key
image_key = uploader.upload_to_drive('/path/to/image.png')

# 批量上传
image_keys = uploader.upload_multiple([
    '/path/to/image1.png',
    '/path/to/image2.png',
])

# 插入图片到文档
uploader.insert_to_docx(doc_id, parent_id, image_key)

# 自动生成报告并上传图片
uploader.generate_report_with_images(
    title='📊 行业调研报告',
    content='# Title\n\n![](image_key_1)\n\nText',
    chart_files=['/path/to/chart1.png', '/path/to/chart2.png']
)
```

**图片上传管道**: upload via `drive/v1/medias/upload_all` with `parent_type=docx_image` and `parent_node=doc_id`, then insert block via `docx/v1/documents/{doc_id}/blocks/{parent_id}/children` using `block_type=27` and `image.file_token=<returned file_token>`.

> ⚠️ 使用 `image.token` + `file_token` 会导致 `1770001 invalid param`，必须用 `image.file_token`。

## 限制

- 图片大小：< 10MB
- 支持格式：PNG, JPG, GIF, WEBP
- 表格：最大 100 行 x 50 列
- 每日上传限额：取决于飞书 API 配额
