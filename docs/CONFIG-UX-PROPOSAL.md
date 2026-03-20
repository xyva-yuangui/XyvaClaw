# xyvaClaw 小白用户体验完整方案 v2

> 目标：小白用户从 `git clone` 到正常对话，3 分钟内完成，零卡点，体验优于所有同类产品。
>
> 本文档基于 **6 款竞品深度调研** + xyvaClaw 全部代码审查，输出可落地方案。

---

## 一、竞品深度调研

### 1.1 市场全景：三大阵营

| 阵营 | 代表产品 | 部署方式 | 目标用户 |
|------|---------|---------|---------|
| **原生 App（零配置）** | QClaw（腾讯）、AutoClaw（智谱）、WorkBuddy（腾讯） | 下载安装包 → 双击 → 完成 | 完全不懂技术的普通用户 |
| **云端托管** | ArkClaw（火山引擎）、JVS Claw（阿里云）、MaxClaw、KimiClaw | 购买云服务 → 浏览器操作 | 不想管服务器的用户 |
| **开源增强** | CoPaw（阿里）、**xyvaClaw**、NanoClaw、Nanobot | `git clone` / `pip install` → 终端 + Web | 有一定动手能力的技术爱好者 |

### 1.2 各竞品详细分析

#### QClaw（腾讯）— 体验标杆

| 维度 | 详情 |
|------|------|
| **安装** | 官网下载 → 双击安装 → 完成。**零终端、零命令行** |
| **模型** | 腾讯免费提供 Token，也支持接入自有 API Key |
| **通道** | **微信 + QQ 原生打通**（扫码绑定，30 秒完成），这是杀手级优势 |
| **飞书** | 支持 |
| **优点** | ① 真正零门槛 ② 微信 QQ 入口（14 亿用户） ③ 免费 Token 降低首次体验成本 |
| **缺点** | ① 内测阶段，功能受限 ② 闭源不可定制 ③ 依赖腾讯生态 ④ 数据隐私受制于腾讯 |

#### AutoClaw（智谱）— 功能最全的原生 App

| 维度 | 详情 |
|------|------|
| **安装** | 官网下载 → 双击 → 手机号注册 → 对话。**1 分钟完成** |
| **模型** | 内置 Pony-Alpha-2（专为 OpenClaw 优化），也支持 GLM-5、DeepSeek、Kimi 等 |
| **通道** | **飞书一键接入**（点击按钮 → 扫码 → 自动配置） |
| **技能** | 预装 50+ 热门技能（搜索、生图、文档处理），95 个技能可选 |
| **特色** | ① 4 个预置分身（通用、调研、监控、浏览器） ② Quick Setup 30 秒个性化 ③ 内置浏览器自动化 |
| **优点** | ① 无需 API Key 即可使用（送 2000 积分） ② 飞书一键接入体验极佳 ③ 预置分身降低使用门槛 |
| **缺点** | ① 积分制收费（用完需充值） ② 智谱生态绑定 ③ 不完全开源 |

#### ArkClaw（火山引擎/字节）— 云端最佳

| 维度 | 详情 |
|------|------|
| **安装** | 订阅 Coding Plan → 点击"创建" → 等待 1-2 分钟 → 完成 |
| **模型** | Doubao-Seed 2.0 + DeepSeek + GLM + Kimi + MiniMax |
| **通道** | **飞书扫码创建机器人**（扫 QR → 填名字 → 自动配置，无需手动输入 App ID/Secret） |
| **特色** | ① **傻瓜式运维**：一键自动修复 ② 内置终端 ③ 自带 Skills Hub 白屏化接入 |
| **优点** | ① 飞书扫码创建机器人（体验最佳） ② 一键修复功能 ③ 7×24 在线 |
| **缺点** | ① 需要付费订阅 Coding Plan（最低 9.9 元/月） ② 云端部署，数据不在本地 |

#### CoPaw（阿里）— 我们最直接的竞品

| 维度 | 详情 |
|------|------|
| **安装** | `pip install copaw` → `copaw init` → `copaw app` → 浏览器打开 `localhost:8088` |
| **模型** | 阿里百炼 Coding Plan 默认，支持自定义 |
| **通道** | **Web UI 中配置飞书**：频道页面 → 填写 App ID/Secret → 启用 → 保存 |
| **特色** | ① 有独立 Web Dashboard（不是 OpenClaw 原生的） ② 配置页面有模型、频道、技能管理 ③ 中文界面 |
| **优点** | ① 开源可定制 ② Web UI 配置（不是终端） ③ 文档详尽 ④ 对百炼生态友好 |
| **缺点** | ① 仍需命令行安装 ② 飞书配置仍需手动输入 App ID/Secret ③ 技能选装不如 AutoClaw 直观 |

#### JVS Claw（阿里云）— 移动端标杆

| 维度 | 详情 |
|------|------|
| **安装** | App Store 下载 → 手机操作 → 完成。**三步，手机即可** |
| **模型** | 阿里云百炼，无需配置 |
| **通道** | 内置 JVS IM |
| **特色** | ① 云端沙盒 ClawSpace（6 核/12GB） ② 动态技能自生长 ③ iOS/Android/Web/Pad 全端 |
| **优点** | ① 手机操作，真正零门槛 ② 云端隔离安全 ③ 文件上传下载无缝交互 |
| **缺点** | ① 完全依赖阿里云 ② 无本地执行能力 ③ 技能生态封闭 |

### 1.3 竞品核心策略总结

| 策略 | 采用的产品 | 效果 |
|------|-----------|------|
| **免费 Token / 积分** | QClaw、AutoClaw、WorkBuddy | 消除"API Key 是什么"的认知门槛 |
| **原生 App 安装** | QClaw、AutoClaw、JVS Claw | 消除"终端是什么"的恐惧 |
| **扫码绑定通道** | QClaw（微信扫码）、ArkClaw（飞书扫码） | 消除手动输入 App ID/Secret 的痛苦 |
| **预置分身/角色** | AutoClaw（4 个预置分身） | 消除"不知道该说什么"的迷茫 |
| **一键修复** | ArkClaw | 消除"坏了不会修"的焦虑 |
| **Web 配置界面** | CoPaw、AutoClaw | 消除"编辑配置文件"的恐惧 |

### 1.4 社区调研的用户四大痛点

来源：OpenClaw 社区调研数据

| 痛点 | 占比 | 对应竞品方案 |
|------|------|------------|
| **部署复杂** | 73% | 原生 App / 云端托管 |
| **安全隐患** | 68% | 沙箱隔离 + 权限管控 |
| **单用户架构** | 55% | 多 Agent 协作 |
| **成本失控** | 42% | Coding Plan 订阅制 |

---

## 二、xyvaClaw 现状诊断

### 2.1 我们的定位

| 层级 | 说明 |
|------|------|
| **OpenClaw 运行时** | 100% 原生，未修改任何源码。提供 Gateway、Dashboard（聊天 UI）、CLI |
| **xyvaClaw 包装层** | 安装脚本 + 配置模板 + `.env` → `openclaw.json` 生成 + 插件 + 技能 |
| **Web Setup Wizard** | 我们自建的 React 应用（`setup-wizard/`），独立于 OpenClaw Dashboard |

**关键限制：OpenClaw Dashboard (`localhost:18789`) 是纯聊天界面，没有 API Key / 飞书凭证配置页面。用户打开 Dashboard 后无法在网页上配置任何密钥。**

### 2.2 当前安装流程（v1.1.5）的 5 个断点

| # | 断点 | 竞品如何解决 | 严重度 |
|---|------|------------|--------|
| 1 | **Web Setup Wizard 存在但从未启动** | CoPaw 有独立 Web 配置页；AutoClaw 有 App 内设置 | 🔴 致命 |
| 2 | **终端只问 API Key，不问飞书** | ArkClaw 飞书扫码自动配置；CoPaw Web UI 填写 | 🔴 致命 |
| 3 | **跳过 API Key 后无引导** | AutoClaw 送免费积分；CoPaw 有明确的配置指引 | 🔴 致命 |
| 4 | **无后续重新配置入口** | CoPaw 的 Web UI 随时可改；AutoClaw 的 Settings 页 | 🟡 严重 |
| 5 | **安装后不知道该说什么** | AutoClaw 有 4 个预置分身；QClaw 有场景引导 | 🟡 体验 |

### 2.3 已有代码资产（90% 完成）

| 文件 | 功能 | 状态 |
|------|------|------|
| `setup-wizard/src/pages/Welcome.jsx` | 助手命名 + 风格选择 | ✅ 完整 |
| `setup-wizard/src/pages/ModelKeys.jsx` | DeepSeek/百炼 API Key + 自定义 Provider + 模型检测 | ✅ 完整 |
| `setup-wizard/src/pages/Channels.jsx` | 飞书配置（含 7 步指引）+ 钉钉/Telegram（即将支持） | ⚠️ webchat 需删 |
| `setup-wizard/src/pages/Skills.jsx` | 38 个技能分组选装 | ✅ 完整 |
| `setup-wizard/src/pages/Advanced.jsx` | 端口/自启动/上下文引擎 | ✅ 完整 |
| `setup-wizard/src/pages/Confirm.jsx` | 配置汇总 + 一键保存 | ✅ 完整 |
| `setup-wizard/server/index.js` | API Key 验证 + 模型检测 + 保存到 `.env` | ✅ 完整 |

---

## 三、xyvaClaw 差异化定位

我们无法（也不应该）去做原生 App 或云端托管——那是大厂的战场。
xyvaClaw 的定位是：**开源社区中，面向中国用户的最佳 OpenClaw 增强方案**。

### 3.1 与竞品的差异化

| 维度 | QClaw / AutoClaw | CoPaw（最直接竞品） | **xyvaClaw（目标）** |
|------|-----------------|-------------------|---------------------|
| **安装** | 原生 App，双击 | pip install + 终端 | `git clone` + **Web Wizard 全程引导** |
| **API Key** | 免费 Token | 终端 + Web UI 配 | **Web Wizard 验证 + 获取指引链接** |
| **飞书** | 扫码 / 一键 | Web UI 手动填写 | **Web Wizard 指引 + 一键验证**（v2: 扫码） |
| **技能** | 预装 50+ | 手动安装 | **可视化选装 38+ 技能，分类清晰** |
| **首次体验** | 预置分身 | 空白聊天 | **预置 Agent 人设 + 对话场景引导** |
| **后续配置** | App 内设置 | Web UI 设置 | **`xyvaclaw setup` 随时打开 Web 向导** |
| **自诊断** | ArkClaw 一键修复 | 无 | **`xyvaclaw doctor` 一键诊断修复** |
| **开源** | ❌ 闭源 | ✅ 开源 | **✅ 开源 + 深度文档** |
| **数据** | 大厂控制 | 本地 | **100% 本地，零上传** |

### 3.2 我们要赢在哪里

1. **安装体验追平 CoPaw，超越原生 OpenClaw**：Web Wizard 全程引导
2. **飞书配置体验接近 ArkClaw**：可视化指引 + 自动验证（远期：扫码创建）
3. **技能选装体验超越所有开源方案**：可视化分类卡片 + 一键批量安装
4. **独有：自诊断修复能力**（学习 ArkClaw）
5. **独有：100% 本地数据主权**（vs QClaw/AutoClaw 的大厂生态锁定）

---

## 四、完整方案：三阶段实施

### 阶段一：恢复 Wizard + 修复断点（v1.2.0，1-2 天）

**核心：让已有的 90% 代码跑起来，立即解决 5 个断点。**

#### 4.1 安装流程（改造后）

```
用户执行: git clone ... && bash xyvaclaw-setup.sh
  ↓
[1] 检查环境 (Node.js ≥ 22, Python ≥ 3.9, ffmpeg)
[2] 安装 OpenClaw 运行时
[3] 部署 xyvaClaw 文件 (agents, extensions, skills, template)
  ↓
[4] ★ 启动 Web Setup Wizard (localhost:19090)
    ├─ 自动打开浏览器
    ├─ 终端显示: "🌐 配置页面已打开: http://localhost:19090"
    ├─ 终端显示: "⏳ 等待你在浏览器中完成配置..."
    ├─ 6 步配置: 命名 → API Key → 飞书 → 技能 → 高级 → 确认
    ├─ 保存后 Wizard 服务自动退出，脚本继续
    └─ 超时 300s 或用户 Ctrl+C → 自动切换终端 fallback
  ↓
[5] 从 .env + wizard JSON 生成 openclaw.json
[6] 注册插件 (lossless-claw, feishu)
[7] 安装技能依赖
  ↓
[8] 启动 Gateway → 自动打开 Dashboard → 用户可以对话了！
```

#### 4.2 具体改动清单

| 文件 | 改动 | 工作量 |
|------|------|--------|
| `xyvaclaw-setup.sh` | Step 4: 启动 Wizard 服务 → 等待保存 → fallback 逻辑 | 中 |
| `setup-wizard/src/pages/Channels.jsx` | 删除 webchat channel（它不是有效 OpenClaw channel ID） | 小 |
| `setup-wizard/src/App.jsx` | 删除 webchat 默认配置 | 小 |
| `setup-wizard/server/index.js` | 保存后自动调用 `restore-config.py` 生成 `openclaw.json` | 小 |

#### 4.3 Wizard Bug 修复

| Bug | 修复 |
|-----|------|
| `webchat` 导致配置验证失败 | 从 `Channels.jsx` CHANNEL_LIST 和 `App.jsx` 默认 state 中移除 |
| Wizard 保存后不生成 `openclaw.json` | `server/index.js` 的 `save-config` 接口里 spawn `restore-config.py` |
| Wizard 退出后脚本不知道 | 用 `wait $WIZARD_PID` 等待进程退出 |

---

### 阶段二：配置门户 + 自诊断（v1.3.0，3-5 天）

**核心：学习 CoPaw 的 Web 配置 + ArkClaw 的一键修复。**

#### 4.4 `xyvaclaw setup` 命令

安装后任何时候运行 `xyvaclaw setup`，重新打开 Web Wizard：

```bash
xyvaclaw setup          # 打开配置向导
xyvaclaw setup --port   # 只改端口
xyvaclaw setup --model  # 只改模型
xyvaclaw setup --feishu # 只改飞书
```

实现方式：在安装脚本中注册一个 shell function 或 alias，执行时：
1. 启动 Wizard 服务 (localhost:19090)
2. 打开浏览器
3. 等待用户保存
4. 自动重新生成 `openclaw.json`
5. 自动重启 Gateway

#### 4.5 `xyvaclaw doctor` 自诊断命令

学习 ArkClaw 的"一键修复"，实现自诊断：

```bash
xyvaclaw doctor
```

输出示例：
```
🔍 xyvaClaw 健康检查
━━━━━━━━━━━━━━━━━━━━
✅ Node.js 22.22.1
✅ Python 3.9.6
✅ OpenClaw 运行时已安装
✅ Gateway 配置文件存在
⚠️  API Key 未配置 → 运行 xyvaclaw setup
✅ lossless-claw 插件已注册
❌ feishu 插件未注册 → 飞书凭证未配置
✅ Gateway 进程运行中 (PID: 12345)
✅ Dashboard 可访问: http://localhost:18789

💡 修复建议: 运行 xyvaclaw setup 配置 API Key 和飞书
   或运行 xyvaclaw doctor --fix 自动修复
```

`xyvaclaw doctor --fix` 自动修复能力：
- 自动重新生成 `openclaw.json`（如果 `.env` 有变更）
- 自动重新注册插件
- 自动重启 Gateway
- 自动修复文件权限

#### 4.6 深度改造 OpenClaw Gateway：配置缺失时的引导页

**这是本方案唯一需要"深度改造"的地方。**

当 Gateway 启动但检测到 `models.providers` 为空时，在 `localhost:18789` **前面加一个反向代理层**，展示引导页而不是空白聊天：

```
用户打开 localhost:18789
  ↓
xyvaClaw Proxy 检测 openclaw.json:
  ├─ providers 有配置 → 透传到 OpenClaw Dashboard（正常使用）
  └─ providers 为空 → 显示 xyvaClaw 引导页:
      "👋 欢迎使用 xyvaClaw！"
      "你还没有配置 AI 模型，请点击下方按钮开始配置"
      [🚀 打开配置向导]  ← 点击后跳转 localhost:19090
      [📖 查看文档]
```

实现方式：一个 50 行的 Node.js HTTP proxy：
- 默认透传所有请求到 OpenClaw Gateway (18789)
- 只在检测到"未配置"时拦截首页请求，返回引导 HTML
- Gateway 实际端口改为 18790（内部），proxy 监听 18789（对外）

**这解决了"用户打开 Dashboard 看到空白聊天框不知所措"的核心问题。**

---

### 阶段三：极致体验（v1.4.0，远期）

#### 4.7 飞书扫码创建机器人（学习 ArkClaw）

当前飞书配置需要用户：
1. 去飞书开放平台创建应用
2. 手动复制 App ID 和 App Secret
3. 粘贴到配置中

ArkClaw 的方案是**扫码自动创建机器人**，用户全程不需要去飞书开放平台。

我们可以在远期实现类似功能：
- Wizard 中显示二维码
- 用户飞书扫码授权
- 后端自动调用飞书 API 创建应用 + 获取凭证
- 自动写入配置

> 注意：这需要我们有一个飞书 ISV 应用（或商店应用），有一定的审核和维护成本。作为远期目标。

#### 4.8 预置对话场景（学习 AutoClaw）

AutoClaw 的"预置分身"思路值得借鉴。安装完成后，在 Dashboard 中提供首次使用引导：

- **快速任务**："帮我总结这个网页"、"帮我写一封邮件"
- **飞书场景**："帮我在飞书群里发个消息"、"帮我安排明天的日程"
- **开发场景**："帮我写一个 Python 脚本"、"帮我审查这段代码"

实现方式：在 Agent 的 system prompt 中预置场景引导（无需改 OpenClaw 代码）。

#### 4.9 Coding Plan 集成指引

学习竞品的 Coding Plan 策略，在 Wizard 的 API Key 页面中：

```
┌─────────────────────────────────────┐
│  💡 还没有 API Key？推荐方案：       │
│                                      │
│  🔥 百炼 Coding Plan（推荐）         │
│     ¥39/月，不限量使用 20+ 模型      │
│     [点击开通 →]                     │
│                                      │
│  💎 DeepSeek                        │
│     注册送 500 万 Token              │
│     [点击获取 →]                     │
│                                      │
│  ☁️ 火山引擎 Coding Plan            │
│     首月 ¥9.9，支持多模型切换        │
│     [点击开通 →]                     │
└─────────────────────────────────────┘
```

---

## 五、与竞品的最终体验对比

### 小白用户 A：只有 API Key，不用飞书

| 步骤 | OpenClaw 原生 | CoPaw | QClaw | **xyvaClaw（方案后）** |
|------|-------------|-------|-------|---------------------|
| 安装 | 终端命令，多次交互选择 | pip install + init | 下载双击 | `git clone` + `bash setup.sh` |
| 配 Key | 终端粘贴（原生 CLI） | Web UI 设置页 | 不需要（免费） | **Web Wizard + 实时验证** |
| 首次对话 | 看到英文 Dashboard | 看到 CoPaw 界面 | 直接微信聊 | **打开 Dashboard + 场景引导** |
| 出问题了 | 自己看终端日志 | 自己看文档 | 内置反馈 | **`xyvaclaw doctor` 一键诊断** |

### 小白用户 B：需要飞书

| 步骤 | OpenClaw 原生 | CoPaw | ArkClaw | **xyvaClaw（方案后）** |
|------|-------------|-------|---------|---------------------|
| 配飞书 | 终端交互 + 手动 | Web UI 填 ID/Secret | **扫码自动创建** | **Wizard 7 步指引 + 验证** |
| 体验 | 差（纯终端） | 中（Web 但无指引） | 优（扫码） | **良+（指引详尽，远期扫码）** |

### 高级用户 C：SSH 无桌面

| 步骤 | **xyvaClaw（方案后）** |
|------|---------------------|
| 安装 | Wizard 超时后自动切终端 fallback |
| 配置 | 终端粘贴 API Key（和现在一样） |
| 后续 | `openclaw configure`（原生 CLI） |

---

## 六、技术架构图

```
┌──────────────────────────────────────────────────┐
│                  用户浏览器                        │
│  ┌──────────────┐    ┌───────────────────────┐   │
│  │ Setup Wizard │    │  OpenClaw Dashboard   │   │
│  │ :19090       │    │  :18789               │   │
│  └──────┬───────┘    └───────────┬───────────┘   │
└─────────┼────────────────────────┼───────────────┘
          │                        │
┌─────────┼────────────────────────┼───────────────┐
│         ▼                        ▼               │
│  ┌──────────────┐    ┌───────────────────────┐   │
│  │ Wizard Server│    │  xyvaClaw Proxy       │   │
│  │ (Node.js)    │    │  (阶段二新增)          │   │
│  │              │    │  ├─ 未配置 → 引导页    │   │
│  │ /api/        │    │  └─ 已配置 → 透传      │   │
│  │  validate-key│    │         ↓              │   │
│  │  save-config │    │  ┌─────────────────┐   │   │
│  └──────┬───────┘    │  │ OpenClaw Gateway│   │   │
│         │            │  │ :18790 (内部)   │   │   │
│         ▼            │  └─────────────────┘   │   │
│  ┌──────────────┐    └───────────────────────┘   │
│  │ .env         │                                 │
│  │ .wizard.json │──→ restore-config.py            │
│  └──────────────┘          ↓                      │
│                    ┌──────────────┐               │
│                    │openclaw.json │               │
│                    └──────────────┘               │
│                                                   │
│  ~/.xyvaclaw/                                     │
└───────────────────────────────────────────────────┘
```

---

## 七、实施优先级与工作量

| 阶段 | 版本 | 核心交付 | 工作量 | 体验提升 |
|------|------|---------|--------|---------|
| **一** | v1.2.0 | 恢复 Wizard + 修复 5 个断点 | **1-2 天** | 🔴→🟢 从"不可用"到"能用" |
| **二** | v1.3.0 | `xyvaclaw setup` + `doctor` + 引导页代理 | **3-5 天** | 🟢→🔵 从"能用"到"好用" |
| **三** | v1.4.0 | 飞书扫码 + 预置场景 + Coding Plan 指引 | **1-2 周** | 🔵→⭐ 从"好用"到"领先" |

---

## 八、决策点

### 必须决策

1. **是否同意三阶段路线？** 还是只做阶段一？
2. **阶段二的 Gateway 代理层**：是否接受"深度改造"（在 Gateway 前加反向代理）？
   - 是 → 解决"空白 Dashboard"问题，体验大幅提升
   - 否 → 只靠终端提示 `xyvaclaw setup`，用户仍可能迷失

### 可选决策

3. **飞书扫码（阶段三）** 是否排入计划？（需要申请飞书 ISV 资质）
4. **Coding Plan 推荐链接** 是否加入 Wizard？（可带来潜在商业合作）
5. **是否为飞书配置指引制作截图/视频？**

---

## 九、不做什么

| 不做 | 原因 |
|------|------|
| 做原生 App（.dmg / .exe） | 那是 QClaw / AutoClaw 的战场，我们维护不了 |
| 做云端托管 | 那是 ArkClaw / JVS Claw 的战场，需要服务器成本 |
| Fork OpenClaw 源码 | 维护成本过高，保持包装层定位 |
| 提供免费 Token | 我们不是大厂，没有补贴能力 |

**我们要做的是：在开源方案中，做到最好的小白友好度。**
**参照物：超越 CoPaw，接近 AutoClaw（在开源能做到的范围内）。**

---

*文档生成时间: 2026-03-20*
*竞品调研来源: QClaw 官网、AutoClaw/Hello-Claw 教程、ArkClaw 部署指南、CoPaw 安装教程、JVS Claw 产品介绍*
*代码审查涉及: xyvaclaw-setup.sh, setup-wizard/\*, installer/restore-config.py, config-base/openclaw.json.template*
