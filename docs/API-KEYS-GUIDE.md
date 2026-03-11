# API Key 获取指南

> 各平台 API Key 的获取方法，图文说明

---

## 1. DeepSeek API Key（推荐首选）

**费用**: 极低成本，按量付费
**模型**: DeepSeek V3.2（通用对话）、DeepSeek Reasoner（深度推理）

### 获取步骤

1. 访问 [platform.deepseek.com](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入「API Keys」页面
4. 点击「Create new API key」
5. 复制生成的 `sk-...` 格式密钥

### 注意事项
- 新注册用户有免费额度
- Key 创建后只显示一次，务必保存
- 格式: `sk-` 开头，约 32 位字符

---

## 2. 百炼 API Key（通义千问/多模型）

**费用**: 按量付费，部分模型有免费额度
**模型**: qwen3.5-plus, qwen3-max, kimi-k2.5, glm-5, MiniMax-M2.5 等

### 获取步骤

1. 访问 [百炼控制台](https://bailian.console.aliyun.com/)
2. 用阿里云账号登录（需实名认证）
3. 左侧菜单 →「API Key 管理」
4. 点击「创建 API Key」
5. 复制生成的 `sk-sp-...` 格式密钥

### 百炼优势
- 一个 Key 可调用多个模型（Qwen、Kimi、GLM、MiniMax）
- 支持图片理解（qwen3.5-plus 支持 image 输入）
- 有推理模型（qwen3-max 支持 reasoning）

### 常见 Base URL

| 用途 | Base URL |
|------|----------|
| 标准 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Coding（更快） | `https://coding.dashscope.aliyuncs.com/v1` |

---

## 3. 飞书应用凭证

**费用**: 免费
**用途**: 通过飞书机器人与 AI 助手对话

详细步骤见 [FEISHU-SETUP.md](./FEISHU-SETUP.md)

### 快速获取

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 在「凭证与基础信息」页面获取:
   - **App ID**: `cli_` 开头
   - **App Secret**: 约 32 位字符串

---

## 4. Tushare Token（量化选股，选填）

**费用**: 基础免费，高级数据需要积分
**用途**: A 股数据获取，支持量化选股引擎

### 获取步骤

1. 访问 [tushare.pro](https://tushare.pro/)
2. 注册账号
3. 进入「个人主页」→「接口 TOKEN」
4. 复制 Token

### 提升权限
- 完善个人信息 +100 积分
- 关注公众号 +50 积分
- 发布研究成果可获得更多积分
- 2000 积分以上可获取更多数据接口

---

## 5. 小红书 Cookie（选填）

**费用**: 免费
**用途**: 小红书内容创作和发布
**注意**: Cookie 会过期，需要定期更新

### 获取步骤

1. 用浏览器登录 [小红书创作者中心](https://creator.xiaohongshu.com/)
2. 按 F12 打开开发者工具
3. 切到 Network 标签
4. 刷新页面，点击任意一个请求
5. 在 Headers 中找到 `Cookie` 字段
6. 复制完整 Cookie 值

---

## 6. 自定义 OpenAI 兼容 Provider

xyvaClaw 支持任何 OpenAI API 兼容的服务商。

### 常见兼容服务

| 服务商 | Base URL | 说明 |
|--------|----------|------|
| OpenRouter | `https://openrouter.ai/api/v1` | 聚合多个模型 |
| Groq | `https://api.groq.com/openai/v1` | 超快推理 |
| Together | `https://api.together.xyz/v1` | 开源模型 |
| Ollama（本地） | `http://localhost:11434/v1` | 本地运行 |
| vLLM（本地） | `http://localhost:8000/v1` | 本地高性能推理 |

### 在向导中添加

配置向导 → 模型页面 → 点击「+ 添加自定义 Provider」→ 填写名称、Base URL、API Key

---

## 安全提醒

- 所有 Key 仅存储在本地 `~/.xyvaclaw/` 目录
- 不要将 Key 提交到 Git 仓库
- 定期轮换 Key 是好习惯
- `.env` 文件权限建议设为 600: `chmod 600 ~/.xyvaclaw/.env`
