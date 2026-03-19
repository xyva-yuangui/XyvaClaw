# v1.1.4 — 一键安装全流程修复

## 概述

修复 **13 个 Bug**，涵盖百炼 Coding Plan 接入、飞书集成、安装脚本三大模块。修改 **8 个文件**，约 **200 行代码变更**。全部修复已通过本地完整安装测试验证（含真实百炼 + 飞书 API Key 测试）。

## 修复清单

### 🤖 百炼 Coding Plan（3 个）

| Bug | 严重性 | 修复 |
|-----|--------|------|
| B1 | 🔴 致命 | `restore-config.py` 百炼 baseUrl 和模型列表修正 |
| B2 | 🔴 致命 | 模板添加 `compat.thinkingFormat`、`agents.defaults.models` 映射、MiniMax maxTokens 修正 |
| B3 | 🟡 中等 | Setup Wizard 百炼验证改用 Coding Plan 端点和正确模型名 (`qwen3-coder-plus`) |

### 💬 飞书集成（3 个）

| Bug | 严重性 | 修复 |
|-----|--------|------|
| F1 | 🔴 致命 | `restore-config.py` 不再清空 plugins，智能合并保留 `feishu_local` + `lossless-claw` |
| F2 | 🟡 中等 | 飞书配置升级为 OpenClaw 官方 `accounts` 嵌套格式 |
| F3 | 🟡 中等 | Setup Wizard 飞书验证传递 `appId` 参数 |

### 🛠 安装脚本（5 个）

| Bug | 严重性 | 修复 |
|-----|--------|------|
| S1 | 🔴 致命 | 修复 `set -euo pipefail` + 中文字符导致脚本崩溃 |
| S2 | 🔴 致命 | 新增 Step 4.5: 自动注册 `lossless-claw` 和 `feishu_local` 插件到 OpenClaw registry |
| S3 | 🟡 中等 | `npx --yes vite build` 自动确认安装提示，不再阻塞 |
| S4 | 🟡 中等 | 自动清理原版 OpenClaw 和其他 Claw 产品（交互/auto 模式均支持） |
| S5 | 🟡 中等 | `feishu/package.json` 补充 `@sinclair/typebox`, `@larksuiteoapi/node-sdk`, `https-proxy-agent`, `zod` |

### 📊 其他（2 个）

- **D1**: Dashboard 无法运行 → 由上游 B1+B2+F1 修复后自动解决
- **M1**: `skill_loading.json` 技能名 `quant-stock-screener` → `quant-strategy-engine`

## 安装方式

```bash
# 一键安装（交互模式）
curl -fsSL https://github.com/xyva-yuangui/XyvaClaw/archive/refs/tags/v1.1.4.tar.gz | tar -xz
cd XyvaClaw-1.1.4
bash xyvaclaw-setup.sh

# 无人值守模式（CI/自动化）
BAILIAN_API_KEY=sk-xxx FEISHU_APP_ID=cli_xxx FEISHU_APP_SECRET=xxx bash xyvaclaw-setup.sh --auto
```

## 修改文件

- `installer/restore-config.py` — 百炼 provider 元数据 + plugins 保留逻辑 + 飞书 accounts 格式
- `config-base/openclaw.json.template` — compat.thinkingFormat + models 映射 + 飞书 accounts
- `setup-wizard/server/index.js` — 百炼验证端点修正
- `setup-wizard/src/components/ApiKeyInput.jsx` — extraBody 参数支持
- `setup-wizard/src/pages/Channels.jsx` — 飞书验证传 appId
- `config-base/config/skill_loading.json` — 技能名修正
- `config-base/extensions/feishu/package.json` — 运行时依赖声明
- `xyvaclaw-setup.sh` — 自动清理 + 插件注册 + pipefail 修复 + vite 构建
