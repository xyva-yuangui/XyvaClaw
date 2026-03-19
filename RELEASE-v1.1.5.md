# v1.1.5 — 安装体验大幅简化

> 发布日期: 2026-03-19

## 🎯 核心改进：从 clone 到对话，只需粘贴一个 API Key

本版本彻底重构了安装流程，解决了用户反馈最多的三个问题：
1. **安装完成后需要填写"网关令牌"** — 已消除
2. **安装过程需要多次 y/n 确认** — 已消除
3. **需要选择"Web 向导"还是"手动编辑"** — 已消除

## ✨ 新特性

### Gateway 本机免认证
- `bind: loopback` 模式下，`auth.mode` 自动设为 `none`
- 打开 `localhost:18789` **直接进入对话界面**，无需输入任何令牌
- 仅在非本机绑定（0.0.0.0 / tailscale）时才启用 token 认证
- 安全性不受影响：loopback 只允许本机访问

### API Key 智能输入
- 安装时直接在终端提示输入 API Key（一个输入框）
- 自动识别 Key 类型：
  - `sk-sp-` → 百炼 Coding Plan → `coding.dashscope.aliyuncs.com`
  - `sk-`（短） → 百炼标准 → `dashscope.aliyuncs.com/compatible-mode`
  - `sk-`（长） → DeepSeek → `api.deepseek.com`
- 自动发送 HTTP 请求验证 Key 是否有效
- 支持环境变量预设：`BAILIAN_API_KEY=xxx bash xyvaclaw-setup.sh`

### 安装流程零确认
- 去掉 sudo wrapper 创建确认
- 去掉开机自启动确认
- 去掉 Gateway 启动确认
- 去掉 Web 向导 / 手动编辑选择
- 安装完成自动启动 Gateway + 自动打开浏览器

## 🔧 Bug 修复（继承自 v1.1.4）

### __API_KEY__ 占位符问题
- 修复 `config-base/agents/main/agent/models.json` 中 `bailian` 和 `deepseek` 的 `__API_KEY__` 占位符覆盖全局配置的问题
- 修复 `config-base/agents/quant-analyst/agent/models.json` 中同样的占位符问题
- 清除 `config-base/agents/main/agent/auth-profiles.json` 中的硬编码 token
- `xyvaclaw-setup.sh` 新增安装后自动清理占位符步骤

### 百炼 API baseUrl 动态选择
- `restore-config.py`：根据 `sk-sp-` / `sk-` 前缀自动选择正确的 baseUrl
- `setup-wizard/server/index.js`：验证端点同步支持动态 baseUrl
- 解决 Coding Plan 密钥使用 `compatible-mode` 端点时的 401 错误

### 飞书集成修复
- 确认 WebSocket 长连接模式 + `im.message.receive_v1` 事件订阅的正确配置
- 文档化飞书开放平台必须操作的 5 个步骤

## 📁 变更文件

```
config-base/openclaw.json.template          # auth.mode: none (loopback 免认证)
config-base/agents/main/agent/models.json   # 移除 __API_KEY__ 占位符
config-base/agents/main/agent/auth-profiles.json  # 清除硬编码 token
config-base/agents/quant-analyst/agent/models.json # 移除 __API_KEY__
installer/restore-config.py                 # loopback 免认证 + 百炼 baseUrl 动态选择
setup-wizard/server/index.js               # 百炼 baseUrl 动态验证
xyvaclaw-setup.sh                          # 重构安装流程 + API Key 智能输入
docs/INSTALL-REDESIGN.md                   # 安装方案设计文档
docs/FULL-AUDIT.md                         # 全面审计报告
```

## 📊 安装体验对比

| 维度 | v1.1.4 及之前 | v1.1.5 |
|------|--------------|--------|
| 用户输入项 | API Key + 网关令牌 + 4个 y/n | **只输入 API Key** |
| 首次打开 Dashboard | 看到令牌输入框 | **直接对话界面** |
| 安装确认次数 | 4 次 | **0 次** |
| 配置方式 | Web 向导或手动编辑 .env | **终端直接粘贴 Key** |
| Key 验证 | 无 | **自动验证 + 类型识别** |

## 🚀 快速安装

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw
bash xyvaclaw-setup.sh
```

或一键安装：
```bash
BAILIAN_API_KEY=sk-sp-your-key bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'
```

## 📋 完整更新日志

- [INSTALL-REDESIGN.md](docs/INSTALL-REDESIGN.md) — 安装方案重新设计
- [FULL-AUDIT.md](docs/FULL-AUDIT.md) — 全面代码审计报告
