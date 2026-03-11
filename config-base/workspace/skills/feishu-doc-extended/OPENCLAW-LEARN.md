# OpenClaw 学习说明：飞书文档自动插图能力

## 目标
让 OpenClaw 在生成飞书文档时，稳定完成“创建文档 → 上传图片 → 插入图片块”，避免出现“文档里无法插图/只能手动拖图”的问题。

---

## 你要记住的关键规则（必须）

1. **图片上传必须使用 `image_type=docx`**
   - 接口：`POST /open-apis/im/v1/images`
   - 如果用 `message` 类型上传，常见结果是能上传但不能插入 docx。

2. **插图必须走 docx block API**
   - 接口：`POST /open-apis/docx/v1/documents/{doc_id}/blocks`
   - 图片块：`block_type = 13`

3. **默认父块使用文档根块 `doc_id`**
   - 未显式提供 `parent_id` 时，使用 `parent_id = doc_id`
   - 插入前先读取 children 计算 `after_position`，用“追加”而不是覆盖。

4. **凭证统一从 `~/.openclaw/secrets/feishu.env` 读取**
   - `FEISHU_APP_ID`
   - `FEISHU_APP_SECRET`
   - 不允许在脚本里写 `YOUR_TENANT_ACCESS_TOKEN` 这类占位串作为正式流程。

5. **错误日志必须打印飞书三元组**
   - `code`
   - `msg`
   - `request_id`
   - 便于权限、参数、租户问题快速定位。

---

## 已落地实现（代码位置）

- 核心上传/插图逻辑：
  - `~/.openclaw/workspace/skills/feishu-doc-extended/feishu_media_upload.py`
- 一键执行入口（完整流水线）：
  - `~/.openclaw/workspace/skills/feishu-doc-extended/generate_ai_manju_report.py`
- 快捷入口：
  - `~/.openclaw/workspace/skills/feishu-doc-extended/quick_report.py`

---

## 推荐执行方式

```bash
python3 ~/.openclaw/workspace/skills/feishu-doc-extended/generate_ai_manju_report.py
```

成功后会输出：
- 文档链接
- 插图成功数/总数
- 失败明细

---

## 故障定位 SOP（让 OpenClaw 按此顺序检查）

1. 检查 `~/.openclaw/secrets/feishu.env` 是否存在且值正确。
2. 检查飞书应用权限是否已开通并发布生效：
   - `docx:document`
   - `docx:document:create`
   - `docs:document.media:upload`
   - `im:message`
3. 确认图片文件存在且 `<10MB`。
4. 查看失败日志中的 `code/msg/request_id`，定位是权限错误还是参数错误。
5. 确认是否按 `image_type=docx` 上传。

---

## 给 OpenClaw 的固定指令模板（可直接复用）

当用户要求“生成飞书文档并插图”时，默认执行：

1. 运行图表生成。
2. 创建 docx 文档。
3. 对每张图片调用 `upload_image(..., image_type="docx")`。
4. 调用 `insert_image_to_docx(doc_id, parent_id=None, image_key=..., after_position=None)`。
5. 返回文档链接 + 插图统计。
6. 若失败，必须返回 `code/msg/request_id` 和修复建议。

禁止：
- 返回“请手动拖图”作为默认方案。
- 使用占位 token 继续执行。

---

## 版本说明

- 更新时间：2026-03-03
- 状态：可执行（已从 TODO/占位改为真实 API 调用链路）
