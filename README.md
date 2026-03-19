<div align="center">

# 🐾 xyvaClaw

### Your Extended Virtual Agent — 你的超级 AI 助手

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey.svg)]()
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-green.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()
[![Skills](https://img.shields.io/badge/Skills-42%2B-orange.svg)]()
[![V5 Pipeline](https://img.shields.io/badge/Cognitive-V5.1-red.svg)]()
[![Feishu](https://img.shields.io/badge/Feishu-Deep%20Integration-purple.svg)]()

**一键部署 · 五阶段认知管道 · 42+ 技能 · 四层记忆系统 · 三级 API 容灾 · 自我进化**

[🇨🇳 中文](#-中文介绍) · [🇬🇧 English](README_EN.md) · [📖 架构文档](docs/PRODUCT-ARCHITECTURE.md) · [📖 Architecture Doc](docs/PRODUCT-ARCHITECTURE_EN.md)

**🌐 官网: [www.xyvaclaw.com](https://www.xyvaclaw.com) · 作者: 圆规（Xyva-yuangui）**

**交流讨论：[QQ群 1087471835](https://qm.qq.com/q/1087471835) · [Discord](https://discord.gg/QABg4Z2Mzu) · [X (Twitter)](https://x.com/dadoudou90)**

</div>

---

## ⚡ 30 秒快速开始

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

> 💡 不会用 git？[下载 ZIP 压缩包](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip)，解压后运行 `bash xyvaclaw-setup.sh`

<details>
<summary><b>📋 详细安装步骤</b></summary>

### 准备工作（只需一次）

1. **获取 AI 模型密钥**（免费注册，二选一即可）：
   - [DeepSeek](https://platform.deepseek.com/api_keys)（推荐，注册即送免费额度）
   - [百炼/通义千问](https://bailian.console.aliyun.com/)（阿里云，一个 Key 调用多个模型）

2. **打开终端**：macOS 按 `Command + 空格` 输入 `Terminal` | Linux 按 `Ctrl + Alt + T`

### 安装过程自动完成

- ✅ 检测并安装缺失依赖（Node.js、Python、ffmpeg）
- ✅ 弹出**图形化配置向导**（浏览器中填写 API Key）
- ✅ 部署 42+ 技能和所有配置
- ✅ 设置开机自启动

### 安装完成后

```bash
xyvaclaw gateway          # 启动 AI 助手
# 浏览器打开 http://localhost:18789
```

</details>

---

## 🇨🇳 中文介绍

xyvaClaw 是基于 [OpenClaw](https://openclaw.ai/) 运行时**深度增强**的 AI 助手平台。它不只是聊天机器人——通过 **V5 五阶段认知管道**，它能**理解意图、分解任务、结构化推理、质量自检**，再给出回答。

```
用户消息 → 认知管道（理解→分析→推理→质检→响应）→ 行动执行 → 记忆沉淀 → 自我迭代
```

---

## 🧠 V5 认知管道 — 核心引擎

每条用户消息经过 **V5 Orchestrator** 统一编排的五阶段管道：

```
┌──────────────────────────────────────────────────────────────┐
│                      V5 Orchestrator                          │
│                                                                │
│  ① 消息分析 → ② 任务分解 → ③ 推理链 → ④ 质量门控 → ⑤ 延迟记录  │
│   (必选)       (复杂任务)    (推理类)   (中高复杂度)    (自动)     │
└──────────────────────────────────────────────────────────────┘
```

| 阶段 | 模块 | 能力 |
|------|------|------|
| **① 理解** | `message-analyzer` | 规则引擎(<1ms) + LLM 深度分析：**12 种意图分类**、5 种对话策略、8 种情绪标签、自动模型路由 |
| **② 分析** | `task-planner` | 复杂任务 → DAG 分解，支持**并行执行**、依赖关系、关键路径识别 |
| **③ 推理** | `multi-step-reasoning` | **5 种推理模板**（投资决策/技术选型/方案评估/根因分析/通用），对抗性正反推理 |
| **④ 质检** | `thought-quality-gate` | 5 维质量自检（逻辑/数据/遗漏/反面/可操作），score < 0.6 必须重做 |
| **⑤ 监控** | `response-latency-monitor` | P50/P95/P99 延迟统计，按 Provider/Model 分组 |

<details>
<summary><b>查看消息分析输出示例</b></summary>

```json
{
  "intent": {
    "primary": "data_analysis",
    "complexity": "complex",
    "urgency": "medium"
  },
  "strategy": {
    "type": "progressive_output",
    "risk_level": "low"
  },
  "emotion": {
    "primary": "curious",
    "intensity": 0.6,
    "tone_suggestion": "formal"
  },
  "routing": {
    "suggested_model": "deepseek/deepseek-reasoner",
    "suggested_skills": ["quant-strategy-engine"],
    "use_reasoning_chain": true,
    "reasoning_template": "investment_decision"
  },
  "action_type": "plan"
}
```

</details>

---

## 💾 四层记忆系统

```
┌────────────────────────────────────────────────┐
│  SESSION-STATE.md    ← 当前会话（WAL 先写后回）    │
├────────────────────────────────────────────────┤
│  memory/YYYY-MM-DD.md  ← 每日记忆              │
├────────────────────────────────────────────────┤
│  MEMORY.md          ← 长期记忆（偏好/规则/项目）   │
├────────────────────────────────────────────────┤
│  .reasoning/SQLite  ← 推理库（结构化检索）        │
└────────────────────────────────────────────────┘
```

| 机制 | 说明 |
|------|------|
| **WAL 协议** | 发现修正/偏好/决策时，**先写 SESSION-STATE.md 再回复**——上下文会消失，文件不会 |
| **Working Buffer** | 上下文 > 60% 时启动危险区缓冲，compaction 后自动恢复 |
| **上下文压缩** | 自研 128K 智能压缩，**35.7% token 节省**，42.8ms 压缩时间 |
| **别名展开** | 搜索前自动展开同义词（`xhs` → `小红书/RED/RedNote`） |
| **自我学习** | 每天至少 1 条学习：失败→ERRORS.md，纠正→LEARNINGS.md，升级→AGENTS.md |

---

## 🔀 模型路由与三级容灾

### 智能路由

| 场景 | 推荐模型 | 上下文窗口 |
|------|----------|------------|
| 默认/闲聊 | DeepSeek V3.2 | 128K |
| 深度分析/推理/代码 | DeepSeek Reasoner | 128K |
| 图片理解 | Qwen3.5+ / Kimi-K2.5 | 1M / 262K |
| 长文本/大上下文 | Qwen3-Max | 262K |

### 三级 Fallback（零停机）

```
Tier 1: DeepSeek (5s timeout)  ──失败──→  Tier 2: Qwen3.5+ (15s)  ──失败──→  Tier 3: Kimi-K2.5 (10s)
```

- 毫秒级超时检测 + 无感切换
- 每 8 小时自动健康检查
- 支持**自定义 Provider**（任何 OpenAI 兼容 API，含自动模型检测）

---

## 🔄 自我迭代引擎

```
发现错误 → error-tracker.json → 自动修复建议 → 验证 → 学习
                                                        ↓
临时记忆 → 每日记忆 → 长期记忆 → 操作规范（AGENTS.md）
```

| 机制 | 说明 |
|------|------|
| **错误追踪** | 按 category 分组，≥3 次同错 → P0 通知用户 |
| **模式库** | 成功率 ≥85% → 升级为规则；<70% → 弱模式告警 |
| **每日维护** | 迭代报告 + Bootstrap 刷新 + 延迟统计 + 推理库摘要 |
| **进化路径** | 临时记忆 → 每日记忆 → 长期记忆 → 操作规范 |

---

## ⚡ 42+ 技能

<details>
<summary><b>🔧 核心（默认启用）</b></summary>

| 技能 | 功能 |
|------|------|
| claw-shell | 安全 Shell 执行，危险命令检测 |
| error-guard | 系统控制面：/status、/flush、/recover |
| browser-pilot | Chrome CDP 浏览器自动化 |
| vision-reader | 图片/OCR 识别 |
| secret-manager | API 密钥安全管理 |
| git | 版本控制操作 |

</details>

<details>
<summary><b>📝 内容创作</b></summary>

| 技能 | 功能 |
|------|------|
| content-creator | 多平台内容生成 |
| auto-video-creator | AI 视频创作 |
| sora-video | Sora 2 视频生成 + 提示词优化 |
| python-dataviz | 数据可视化 |
| chart-image | 图表生成 |
| excel-xlsx | Excel 读写 |
| word-docx | Word 文档生成 |
| pptx-generator | PPT 创建 |
| pdf-processor | PDF 处理（提取/合并/拆分） |
| qwen-image | AI 图片生成 |

</details>

<details>
<summary><b>📊 数据与量化</b></summary>

| 技能 | 功能 |
|------|------|
| quant-strategy-engine | A 股量化选股、因子分析、策略回测 |
| auto-researcher | 自动化研究与分析 |
| rag-knowledge-base | 本地 RAG 知识库 |
| knowledge-graph-memory | 知识图谱记忆 |

</details>

<details>
<summary><b>🤖 自动化</b></summary>

| 技能 | 功能 |
|------|------|
| cron-scheduler | 定时任务（Cron 管理） |
| workflow | 多步骤自动化流水线 |
| batch | 批量任务处理 |
| web-scraper | 网页内容提取 |
| system-control | 系统截图、信息 |
| email | 邮件读取/搜索/发送（IMAP/SMTP） |
| voice | TTS（200+ 语音）+ STT（Whisper） |

</details>

<details>
<summary><b>🔄 自我进化</b></summary>

| 技能 | 功能 |
|------|------|
| self-improving-agent | 错误学习、纠正记录、知识提升 |
| proactive-agent | WAL、Working Buffer、主动任务发现 |
| effect-tracker | 技能效果追踪（SQLite） |
| code-review | 自动代码审查 |
| test-runner | 自动化测试 |

</details>

<details>
<summary><b>💬 社交媒体与通信</b></summary>

| 技能 | 功能 |
|------|------|
| xhs-creator | 小红书内容创作 |
| xhs-publisher | 小红书自动发布 |
| smart-messenger | 智能消息路由 |
| feishu-doc-extended | 飞书文档深度操作 |
| reddit-readonly | Reddit 内容抓取 |
| miniflux-news | RSS 新闻聚合 |

</details>

---

## � 飞书深度集成

- **112 个 TypeScript 源文件**覆盖飞书几乎所有 API
- 消息、文档、多维表格、日历、审批、云盘、Wiki
- 企业级可靠性：去重、串行调度、超时看门狗、降级回退

---

## 🏗 系统架构

```
┌─────────┐     ┌──────────────┐     ┌───────────────────┐
│  用户     │────→│  飞书/WebChat │────→│  OpenClaw Gateway  │
│  消息     │     │  消息通道      │     │  (port 18789)      │
└─────────┘     └──────────────┘     └────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼───────┐          ┌──────▼──────┐
              │ Bootstrap  │            │ V5 Orchestrator│          │   Skills    │
              │ Bundle     │            │ 认知管道        │          │  42 个技能   │
              │ (SOUL/USER │            │                │          │             │
              │ /TOOLS/... │            │ ① 消息分析      │          │ quant/xhs/  │
              │  → JSON)   │            │ ② 任务分解      │          │ browser/    │
              └────────────┘            │ ③ 推理链        │          │ video/...   │
                                        │ ④ 质量门控      │          └──────┬──────┘
                                        │ ⑤ 延迟记录      │                 │
                                        └───────┬───────┘                  │
                                                │                          │
                    ┌───────────────────────────┼──────────────────────────┤
                    │                           │                          │
              ┌─────▼─────┐            ┌────────▼────────┐         ┌──────▼──────┐
              │ 记忆系统    │            │   模型路由       │         │  效果追踪    │
              │            │            │                  │         │             │
              │ SESSION    │            │ DS V3.2 (主力)    │         │ SQLite      │
              │ MEMORY.md  │            │ DS Reasoner      │         │ 执行指标     │
              │ .reasoning │            │ Qwen3.5+ (图片)   │         │ 业务指标     │
              │ /SQLite    │            │ 3级 Fallback      │         │ 周报/月报    │
              └────────────┘            └─────────────────┘         └─────────────┘
```

### 文件结构

```
~/.xyvaclaw/
├── .openclaw/
│   └── openclaw.json          # Gateway 主配置
├── workspace/
│   ├── SOUL.md                # AI 人格定义
│   ├── IDENTITY.md            # AI 身份
│   ├── USER.md                # 用户画像
│   ├── AGENTS.md              # 核心操作规范 (V5.1)
│   ├── TOOLS.md               # 工具环境速查
│   ├── HEARTBEAT.md           # 心跳任务
│   ├── MEMORY.md              # 长期记忆
│   ├── SESSION-STATE.md       # 会话状态
│   ├── skills/                # 42 个技能模块
│   ├── scripts/               # V5 认知管道脚本
│   ├── memory/                # 每日记忆
│   ├── .reasoning/            # 推理库 (SQLite)
│   ├── .learnings/            # 学习记录
│   └── state/                 # 运行时状态
├── extensions/
│   ├── feishu/                # 112 TS 文件 — 飞书集成
│   └── lossless-claw/         # 无损上下文引擎
├── agents/                    # 多 Agent 配置
└── logs/                      # 运行日志
```

---

## � 高级安装选项

### 无人值守安装

```bash
# macOS — 全自动
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'

# Linux — 全自动
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'
```

| 环境变量 | 必填 | 说明 |
|----------|------|------|
| `DEEPSEEK_API_KEY` | 二选一 | [DeepSeek API Key](https://platform.deepseek.com/api_keys) |
| `BAILIAN_API_KEY` | | [百炼 API Key](https://bailian.console.aliyun.com/) |
| `FEISHU_APP_ID` | 可选 | 飞书机器人 App ID |
| `FEISHU_APP_SECRET` | 可选 | 飞书机器人 App Secret |
| `ASSISTANT_NAME` | 可选 | 自定义助手名称 |

### 系统要求

| 要求 | 详情 |
|------|------|
| **操作系统** | macOS 12+ 或 Linux (Ubuntu 22+, Debian 12+, CentOS 8+) |
| **Node.js** | 22+（缺失时自动安装） |
| **Python** | 3.10+（缺失时自动安装） |
| **API Key** | 至少一个：[DeepSeek](https://platform.deepseek.com/api_keys) 或 [百炼](https://bailian.console.aliyun.com/) |

---

## 📖 文档

| 文档 | 说明 |
|------|------|
| [产品架构说明书](docs/PRODUCT-ARCHITECTURE.md) | V5 认知管道、记忆系统、模型路由完整技术文档 |
| [Product Architecture (EN)](docs/PRODUCT-ARCHITECTURE_EN.md) | Full technical documentation in English |
| [产品介绍](docs/PRODUCT-INTRODUCTION.md) | 核心能力与竞争优势 |
| [API 密钥指南](docs/API-KEYS-GUIDE.md) | 各 Provider 密钥获取方法 |
| [飞书配置](docs/FEISHU-SETUP.md) | 飞书机器人配置教程 |
| [常见问题](docs/FAQ.md) | FAQ |

---

## 🤝 贡献

欢迎贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw && git checkout -b feature/your-feature
# 开发修改
git push origin feature/your-feature
# 在 GitHub 上提交 PR
```

---

## 📄 许可证

[MIT License](LICENSE) — 个人和商业使用均免费。

---

## ⭐ Star History

如果 xyvaClaw 对你有帮助，请给个 ⭐ 吧！这是我持续改进的动力。

If xyvaClaw helps you, please give it a ⭐! It motivates us to keep improving.

---

<div align="center">

**xyvaClaw** — *从 Claw 到 xyvaClaw，不是替代，是进化。*

*From Claw to xyvaClaw, not a replacement, but an evolution.*

Made with ❤️ by the xyvaClaw team

</div>
