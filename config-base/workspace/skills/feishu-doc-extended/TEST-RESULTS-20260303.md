# 飞书文档自动插图测试报告

**测试时间**：2026-03-03 20:24  
**测试人员**：AI 助手

---

## 📊 测试结果

### ✅ 成功的功能

| 功能 | API | 状态 | 说明 |
|------|-----|------|------|
| 获取 tenant token | `/auth/v3/tenant_access_token/internal` | ✅ 通过 | 凭证配置正确 |
| 图片上传 | `/im/v1/images` | ✅ 通过 | `image_type=message` |
| 获取 image_key | - | ✅ 通过 | 可用于文档引用 |

### ❌ 失败的功能

| 功能 | API | 错误 | 原因 |
|------|-----|------|------|
| 图片上传 (docx) | `/im/v1/images` | 234001 | `image_type=docx` 参数错误 |
| 插入图片到文档 | `/docx/v1/documents/{id}/blocks` | 404 | API 路径不存在或需额外权限 |

---

## 🔍 详细测试过程

### 测试 1：图片上传（image_type=docx）

**请求**：
```bash
POST /open-apis/im/v1/images
Headers: Authorization: Bearer {token}
Data: image_type=docx
Files: image=@chart.png
```

**响应**：
```json
{
  "code": 234001,
  "msg": "Invalid request param."
}
```

**结论**：❌ 失败 - 参数错误

---

### 测试 2：图片上传（image_type=message）

**请求**：
```bash
POST /open-apis/im/v1/images
Headers: Authorization: Bearer {token}
Data: image_type=message
Files: image=@chart.png
```

**响应**：
```json
{
  "code": 0,
  "data": {
    "image_key": "img_v3_02ve_xxx"
  }
}
```

**结论**：✅ 成功

---

### 测试 3：插入图片到文档

**请求**：
```bash
POST /open-apis/docx/v1/documents/{doc_id}/blocks
Headers: 
  Authorization: Bearer {token}
  Content-Type: application/json
Body:
{
  "parent_id": "{doc_id}",
  "after_position": 0,
  "block": {
    "block_type": 13,
    "image": {
      "image_key": "img_v3_xxx"
    }
  }
}
```

**响应**：
```
404 page not found
```

**结论**：❌ 失败 - API 路径不存在

---

## 💡 解决方案

### 当前可用方案

**工作流程**：
1. 使用 `image_type=message` 上传图片 ✅
2. 获取 `image_key` ✅
3. 手动拖拽图片到文档（30 秒）⚠️

**原因**：
- 飞书 docx 插入 API 可能需要额外权限
- 或 API 路径与公开文档不一致

### 待解决问题

1. **图片上传类型**
   - `image_type=docx` 返回 234001 错误
   - 使用 `image_type=message` 可成功上传
   - 但获取的 image_key 可用于文档引用

2. **文档插入 API**
   - `/docx/v1/documents/{id}/blocks` 返回 404
   - 可能需要：
     - 额外 API 权限申请
     - 或企业版特定功能
     - 或正确的 API 路径

---

## 📋 配置检查清单

### ✅ 已配置

- [x] `~/.openclaw/secrets/feishu.env`
  - `FEISHU_APP_ID=cli_a9f0bf019038dcc4`
  - `FEISHU_APP_SECRET=AYjCkONyz898KSphZSAISejZH5yiAwFU`
- [x] 飞书应用权限
  - `docx:document`
  - `docx:document:create`
  - `im:message`

### ⚠️ 待确认

- [ ] `docs:document.media:upload` 权限是否已开通
- [ ] 飞书应用是否已发布生效
- [ ] 是否需要企业版功能

---

## 🚀 下一步行动

### 短期（今天）

- [ ] 联系飞书开放平台确认正确的插入 API
- [ ] 检查应用权限是否完整
- [ ] 测试其他可能的 API 路径

### 中期（本周）

- [ ] 申请额外权限（如需要）
- [ ] 或实现替代方案（如使用云盘中转）

### 长期

- [ ] 实现完整的自动化流程
- [ ] 添加错误重试机制
- [ ] 支持批量上传

---

## 📞 联系飞书开放平台

**问题描述**：
1. 图片上传 API 使用 `image_type=docx` 返回 234001 错误
2. 文档插入 API `/docx/v1/documents/{id}/blocks` 返回 404

**需要的信息**：
- 正确的图片上传参数
- 正确的文档插入 API 路径
- 需要的权限列表

**Log ID**：
- 上传失败：`20260303202102E58277C94AB6511BDAD8`
- 插入失败：`20260303202311EFF8F401E65F6E2A6F0A`

---

**测试完成时间**：2026-03-03 20:24  
**状态**：⚠️ 部分通过（上传成功，插入失败）
