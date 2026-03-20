# xyvaClaw v2.0.0 — 小白友好大版本

> 发布日期: 2026-03-20
> 基于 6 款竞品深度调研，全面重构安装配置体验

---

## 🎯 核心升级

**从"能装上"到"好用"的跨越。** v2.0.0 是 xyvaClaw 有史以来最大的体验升级，目标是让完全不懂技术的用户也能在 3 分钟内完成安装并开始对话。

### 安装体验对比

| 维度 | v1.x | v2.0.0 |
|------|------|--------|
| 配置方式 | 终端粘贴 API Key | **Web 配置向导**（6 步可视化） |
| 飞书配置 | 手动编辑 .env 文件 | **向导中 7 步图文指引 + 自动验证** |
| 技能选装 | 无法选择 | **可视化分类卡片，一键勾选** |
| API Key 获取 | 无指引 | **Coding Plan 推荐 + 一键跳转** |
| 首次使用 | 空白聊天框 | **预置场景引导 + 智能引导页** |
| 出问题了 | 自己看日志 | **`xyvaclaw doctor` 一键诊断修复** |
| 后续改配置 | 手动编辑文件 | **`xyvaclaw setup` 随时打开配置向导** |

---

## ✨ 新功能

### 1. Web Setup Wizard 接入安装流程
安装过程中自动启动 Web 配置向导 (`localhost:19090`)，用户在浏览器中完成所有配置：
- **步骤 1**: 为 AI 助手取名 + 选择风格
- **步骤 2**: 配置 API Key（DeepSeek / 百炼 / 自定义），含实时验证
- **步骤 3**: 配置飞书机器人（含 7 步详细指引），可选
- **步骤 4**: 选装 38+ 技能（分类卡片展示）
- **步骤 5**: 高级设置（端口、自启动）
- **步骤 6**: 确认汇总 → 一键保存

保存后自动生成 `openclaw.json`，向导退出，安装继续。

### 2. xyvaClaw CLI 升级
`xyvaclaw` 命令从简单的 OpenClaw 代理升级为完整 CLI：
```bash
xyvaclaw setup          # 打开 Web 配置向导（修改 API Key / 飞书 / 技能）
xyvaclaw doctor         # 健康检查（环境、配置、插件、Gateway 全面诊断）
xyvaclaw doctor --fix   # 自动修复问题
xyvaclaw status         # 查看运行状态
xyvaclaw help           # 查看所有命令
xyvaclaw gateway        # 启动 Gateway（透传 OpenClaw）
```

### 3. 智能引导代理层
在 OpenClaw Gateway 前新增 HTTP 反向代理：
- 检测到 API Key **未配置** → 显示美观的引导页（配置向导入口 + 获取 Key 指引）
- 检测到 API Key **已配置** → 透传到 OpenClaw Dashboard（完全透明）
- 支持 WebSocket 透传（OpenClaw 实时功能不受影响）
- 引导页每 5 秒自动检测，配置完成后自动刷新为 Dashboard

### 4. Coding Plan 获取指引
Wizard 的 API Key 页面新增"还没有 API Key？"推荐面板：
- 🔥 **百炼 Coding Plan**（推荐）：¥39/月不限量
- 💎 **DeepSeek**：注册送 500 万 Token
- ☁️ **火山引擎 Coding Plan**：首月 ¥9.9

### 5. 预置对话场景
首次使用时，AI 助手主动展示能力场景引导：
- 📝 日常效率：邮件、总结、计划
- 💻 技术开发：脚本、审查、调试
- 📊 内容创作：文案、翻译、PPT

---

## 🐛 Bug 修复

- **webchat 频道导致配置验证失败**: 从 Wizard 频道列表和默认配置中移除 `webchat`（不是有效的 OpenClaw channel ID）
- **Wizard 保存后不生成 openclaw.json**: `server/index.js` 保存后自动调用 `restore-config.py`

---

## 📁 变更文件

| 文件 | 变更 |
|------|------|
| `xyvaclaw-setup.sh` | Step 4 改为启动 Web Wizard；xyvaclaw CLI 升级为完整 CLI (setup/doctor/status)；Gateway 启动改为代理模式 |
| `setup-wizard/src/pages/Channels.jsx` | 删除 webchat channel |
| `setup-wizard/src/App.jsx` | 删除 webchat 默认配置 |
| `setup-wizard/src/pages/ModelKeys.jsx` | 新增 Coding Plan 获取指引面板 |
| `setup-wizard/server/index.js` | 保存后调用 restore-config.py；新增 spawn 导入 |
| `installer/gateway-proxy.js` | **新增** — Gateway 智能引导代理层 |
| `templates/SOUL.md.template` | 新增 First Conversation 预置场景引导 |
| `docs/CONFIG-UX-PROPOSAL.md` | 升级为 v2，含 6 款竞品深度调研 |

---

## 🔄 升级方式

```bash
cd XyvaClaw-main
git pull origin main
bash xyvaclaw-setup.sh
```

安装脚本会自动更新 xyvaclaw CLI 和所有配置。

---

## 📊 竞品对标

本版本基于 QClaw（腾讯）、AutoClaw（智谱）、ArkClaw（字节）、CoPaw（阿里）、JVS Claw（阿里云）、WorkBuddy（腾讯）6 款竞品的深度调研，在开源方案中实现了最佳的小白用户友好度。

详见: `docs/CONFIG-UX-PROPOSAL.md`
