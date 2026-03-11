# Feishu Doc Extended - 飞书文档扩展工具

完全自动化的飞书文档报告生成系统

---

## 🎯 功能

- ✅ 生成数据图表（Python + matplotlib）
- ✅ 创建飞书文档
- ✅ 上传图片到文档
- ✅ 插入图片到指定位置
- ✅ 创建表格
- ✅ 发送文档链接到群聊

---

## 📦 安装

### 依赖

```bash
pip3 install matplotlib requests
```

### 配置

1. 获取飞书 API 凭证：
   - 登录 [飞书开放平台](https://open.feishu.cn/)
   - 创建企业自建应用
   - 获取 App ID 和 App Secret

2. 配置到 OpenClaw：
   ```bash
   mkdir -p ~/.openclaw/secrets
   cat > ~/.openclaw/secrets/feishu.env << 'EOF'
   FEISHU_APP_ID=cli_xxxxxxxxxxxx
   FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
   EOF
   ```

3. 启用权限（已在飞书后台配置）：
   - `docs:document.media:upload`
   - `docx:document`
   - `docx:document:create`
   - `im:message`

---

## 🚀 使用

### 方法 1：一键生成报告

```bash
cd ~/.openclaw/workspace/skills/feishu-doc-extended
python3 generate_ai_manju_report.py
```

该脚本会自动执行：
1. 生成图表
2. 创建 docx 文档
3. 上传图片（`image_type=docx`）
4. 自动插入图片到文档根块并输出最终文档链接

### 方法 2：分步执行

```python
from auto_report_generator import AutoReportGenerator

generator = AutoReportGenerator()

# 1. 生成图表
generator.generate_charts()

# 2. 创建文档
generator.create_document("报告标题", "Markdown 内容")

# 3. 发送图表到群聊
for chart in generator.charts:
    generator.send_to_group("图表说明", files=[chart])

# 4. 发送文档链接
generator.send_to_group("📄 完整报告：https://feishu.cn/docx/xxx")
```

### 方法 3：使用 OpenClaw 工具

在 OpenClaw 中调用：

```json
{
  "tool": "feishu_doc_extended",
  "action": "generate_report",
  "params": {
    "title": "📊 AI 漫剧行业深度调研报告",
    "content": "# Title\n\n![](/path/to/chart.png)",
    "chart_files": [
      "/path/to/chart1.png",
      "/path/to/chart2.png"
    ]
  }
}
```

---

## 📊 图表生成

图表脚本：`/Users/momo/.openclaw/workspace/output/generate_charts.py`

生成的图表：
1. `chart_market_size.png` - 市场规模对比
2. `chart_age_distribution.png` - 年龄分布饼图
3. `chart_cost_comparison.png` - 成本对比柱状图
4. `chart_revenue_model.png` - 变现模式占比

---

## 🔧 API 参考

### FeishuMediaUploader

```python
from feishu_media_upload import FeishuMediaUploader

uploader = FeishuMediaUploader()  # 自动读取 ~/.openclaw/secrets/feishu.env

# 创建文档
doc_id, doc_url = uploader.create_document('报告标题')

# 上传图片（docx）
image_key = uploader.upload_image('/path/to/image.png', image_type='docx')

# 插入图片到文档
uploader.insert_image_to_docx(doc_id, parent_id=None, image_key=image_key, after_position=None)

# 创建表格
uploader.create_table_in_docx(doc_id, parent_id, table_data)
```

---

## 📝 示例报告结构

```markdown
# 📊 报告标题

## 🎯 核心结论

1. 结论 1
2. 结论 2

## 📈 第一部分

![图表 1](file:///path/to/chart1.png)

文字说明...

## 👥 第二部分

![图表 2](file:///path/to/chart2.png)

文字说明...

## 📌 结论

总结...
```

---

## ⚠️ 限制

- 图片大小：< 10MB
- 支持格式：PNG, JPG, GIF, WEBP
- 表格：最大 100 行 x 50 列
- 需要飞书企业版 API 权限

---

## 🐛 故障排除

### 图片上传失败

检查：
1. 文件路径是否正确
2. 文件大小是否 < 10MB
3. `~/.openclaw/secrets/feishu.env` 中 `FEISHU_APP_ID/FEISHU_APP_SECRET` 是否有效
4. 飞书应用权限是否已发布并生效（`docx:document` / `docx:document:create` / `docs:document.media:upload` / `im:message`）

### 文档创建失败

检查：
1. 飞书权限是否配置
2. tenant access token 是否过期
3. 网络是否通畅

### 图表生成失败

检查：
1. matplotlib 是否安装
2. 中文字体是否支持
3. 输出目录是否有写权限

---

## 📞 支持

遇到问题请查看：
- [飞书开放平台文档](https://open.feishu.cn/document/ukTMukTMukTM/uEjNwUjLxYDM14SM2ATN)
- [OpenClaw 文档](https://docs.openclaw.ai)

---

**版本**：1.0.0  
**更新时间**：2026-03-03
