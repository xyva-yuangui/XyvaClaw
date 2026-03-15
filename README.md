<div align="center">

# 🐾 xyvaClaw

### Your Extended Virtual Agent — 你的超级 AI 助手

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey.svg)]()
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-green.svg)]()
[![Skills](https://img.shields.io/badge/Skills-42%2B-orange.svg)]()
[![Feishu](https://img.shields.io/badge/Feishu-Deep%20Integration-purple.svg)]()

**一键部署。自我进化。42+ 技能。五级模型容灾。飞书深度集成。**

**One-click deploy. Self-evolving. 42+ skills. 5-level model fallback. Deep Feishu/Lark integration.**

**🌐 官网: [www.xyvaclaw.com](https://www.xyvaclaw.com) · 作者: 圆规（Xyva-yuangui）**

**交流讨论：[QQ群 1087471835](https://qm.qq.com/q/1087471835) · [Discord](https://discord.gg/QABg4Z2Mzu) · [X (Twitter)](https://x.com/dadoudou90)**

</div>

---

## ⚡ 30 秒快速开始

> **完全不懂代码？** 别担心！只需 3 步即可拥有你的 AI 助手。

### 📋 准备工作（只需一次）

1. **获取 AI 模型密钥**（免费注册，二选一即可）：
   - [DeepSeek](https://platform.deepseek.com/api_keys)（推荐，注册即送免费额度）
   - [百炼/通义千问](https://bailian.console.aliyun.com/)（阿里云，一个 Key 调用多个模型）

2. **打开终端**：
   - **macOS**：按 `Command + 空格`，输入 `Terminal`，回车
   - **Linux**：按 `Ctrl + Alt + T`
   - **Windows**：暂不支持原生安装，推荐使用 [WSL2](https://learn.microsoft.com/zh-cn/windows/wsl/install)

### 🚀 一键安装

把下面的命令**复制粘贴**到终端，按回车：

```bash
# macOS / Linux 一键安装（自动安装所有依赖）
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

> 💡 **不会用 git？** 也可以直接 [下载 ZIP 压缩包](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip)，解压后在终端进入文件夹运行 `bash xyvaclaw-setup.sh`

安装过程会自动：
- ✅ 检测并安装缺失依赖（Node.js、Python、ffmpeg）
- ✅ 弹出**图形化配置向导**（在浏览器中填写 API Key 即可）
- ✅ 部署 42+ 技能和所有配置
- ✅ 设置开机自启动

### 🎉 安装完成后

```bash
# 启动你的 AI 助手
xyvaclaw gateway

# 然后在浏览器打开（默认地址）：
# http://localhost:18789
```

首次启动会下载 embedding 模型（约 70MB），请耐心等待约 1 分钟。

---

> **[📖 详细安装指南](docs/API-KEYS-GUIDE.md)** · **[❓ 常见问题](docs/FAQ.md)** · **[English Guide](#-english)**

---

## 🇨🇳 中文介绍

### xyvaClaw 是什么？

xyvaClaw 是基于 [OpenClaw](https://openclaw.ai/) 运行时**深度增强**的 AI 助手平台。它不只是一个聊天机器人——它能**思考、行动、学习、进化**，通过终端、浏览器或飞书群成为你的数字伙伴。

可以理解为 **OpenClaw 的增强版**：相同的引擎，但预调好的模型、经过实战检验的技能、企业级飞书集成，以及让助手每天变得更聪明的进化引擎。

### 核心竞争力

#### 🧠 理解力 — 不只是听懂，是真的懂
- **无损上下文引擎**：对话再长也不会"忘事"
- **四层记忆系统**：会话→日记忆→长期记忆→知识图谱
- **多模态输入**：文字、图片、文档、截图全能理解
- **别名映射**：用户自定义称呼，让对话更自然

#### 🔬 推理力 — 不只是回答，是深度分析
- **双模型推理**：日常用 DeepSeek V3.2，复杂问题自动切换推理模型
- **五级容灾**：任何模型故障都不影响服务
- **量化选股引擎**：内置 A 股多因子筛选、技术分析

#### 🔄 自我进化 — 越用越懂你
- **错误学习**：犯错自动记录，下次直接规避
- **效果追踪**：每个决策都追踪结果，形成正反馈
- **主动行动**：不等你问，主动发现任务并执行
- **自我反思**：周期性分析行为模式，持续优化

#### ⚡ 执行力 — 不只是建议，是直接帮你干
- **42 个技能**：浏览器自动化、文档处理、PPT/PDF、语音对话、邮件、视频制作...
- **定时任务**：自动化日报、数据同步、内容发布
- **工作流引擎**：多步骤自动化流水线

#### 💬 飞书集成 — 用聊天指挥一切
- **112 个 TypeScript 源文件**覆盖飞书几乎所有 API
- 消息、文档、多维表格、日历、审批、云盘、Wiki
- 企业级可靠性：去重、串行调度、超时看门狗、降级回退

---

## 🌍 English

### What is xyvaClaw?

xyvaClaw is an **enhanced AI assistant platform** built on the [OpenClaw](https://openclaw.ai/) runtime. It transforms a bare AI chatbot into a **thinking, acting, self-improving digital partner** that works alongside you — through your terminal, your browser, or your Feishu/Lark groups.

Think of it as **OpenClaw on steroids**: same engine, but with pre-tuned models, battle-tested skills, enterprise-grade Feishu integration, and an evolution engine that makes your assistant smarter every day.

### Why xyvaClaw?

| | Raw OpenClaw | xyvaClaw |
|---|---|---|
| **Setup** | Manual JSON editing, schema knowledge required | One-click installer + Web wizard |
| **Models** | BYO (bring your own) | Pre-configured DeepSeek V3.2 + Bailian (Qwen/Kimi/GLM/MiniMax) |
| **Resilience** | Single model | 5-level automatic fallback — zero downtime |
| **Context** | Native compression (lossy) | **Lossless-Claw engine** — never forgets mid-conversation |
| **Memory** | Basic MEMORY.md | 4-tier memory: session → daily → long-term → knowledge graph |
| **Feishu/Lark** | Basic message send/receive | **112 TypeScript source files** covering nearly every Feishu API |
| **Skills** | Install one by one | **42 skills pre-installed**, organized by category |
| **Self-Evolution** | ❌ None | ✅ Error learning + effect tracking + proactive reflection |
| **Reasoning** | Depends on user's model choice | Auto-selects optimal model per task complexity |
| **Ops** | Manual | Health checks, log rotation, auto-start on boot |
| **Docs** | English only | Full Chinese + English documentation |

### Quick Start (English)

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

Or download: **[ZIP Package](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip)**

### Core Capabilities

- **🧠 Lossless Context** — Long conversations without information loss, 4-tier memory system
- **🔬 Dual-Model Reasoning** — Auto-selects optimal model per task, 5-level fallback
- **🔄 Self-Evolution** — Error learning, effect tracking, proactive reflection
- **⚡ 42 Built-in Skills** — Browser automation, document processing, PPT/PDF, voice, email, video creation
- **💬 Deep Feishu/Lark** — 112 TypeScript source files covering nearly every Feishu API

---

## 🚀 Advanced Install Options

### Unattended Install (zero interaction)

```bash
# macOS — fully automatic, no prompts
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'

# Linux — fully automatic
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'
```

**Environment variables supported in `--auto` mode:**

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | One of these | [DeepSeek API Key](https://platform.deepseek.com/api_keys) |
| `BAILIAN_API_KEY` | required | [百炼 API Key](https://bailian.console.aliyun.com/) |
| `FEISHU_APP_ID` | Optional | Feishu Bot App ID |
| `FEISHU_APP_SECRET` | Optional | Feishu Bot App Secret |
| `ASSISTANT_NAME` | Optional | Custom assistant name |

### What the installer does:
1. ✅ Check and install dependencies (Node.js 22+, Python 3, ffmpeg)
2. ✅ Install OpenClaw runtime
3. ✅ Launch Web Setup Wizard (or auto-configure in `--auto` mode)
4. ✅ Deploy configs, skills (42+), and extensions
5. ✅ Generate identity files
6. ✅ Register system service (auto-start on boot)

### Requirements

| Requirement | Details |
|-------------|----------|
| **OS** | macOS 12+ or Linux (Ubuntu 22+, Debian 12+, CentOS 8+) |
| **Node.js** | 22+ (auto-installed if missing) |
| **Python** | 3.10+ (auto-installed if missing) |
| **API Key** | At least one: [DeepSeek](https://platform.deepseek.com/api_keys) or [Bailian](https://bailian.console.aliyun.com/) |

---

## 🛠 Skills (42+)

<details>
<summary><b>Core (default)</b></summary>

| Skill | Description |
|-------|-------------|
| secret-manager | Secure API key management |
| claw-shell | Terminal command execution |
| error-guard | Automatic error handling |
| vision-reader | Image/OCR recognition |
| browser-pilot | Browser automation |
| git | Version control |

</details>

<details>
<summary><b>Content Creation</b></summary>

| Skill | Description |
|-------|-------------|
| content-creator | Multi-platform content generation |
| auto-video-creator | AI video creation |
| python-dataviz | Data visualization |
| chart-image | Chart generation |
| excel-xlsx | Excel read/write |
| word-docx | Word document generation |
| pptx-generator | PowerPoint presentation creation |
| pdf-processor | PDF extract, merge, split, convert |

</details>

<details>
<summary><b>Feishu Enhanced</b></summary>

| Skill | Description |
|-------|-------------|
| feishu-doc-extended | Advanced Feishu doc ops (images, tables) |
| smart-messenger | Enhanced message management |

</details>

<details>
<summary><b>Data & Quantitative</b></summary>

| Skill | Description |
|-------|-------------|
| quant-strategy-engine | A-share quantitative stock screening |
| auto-researcher | Automated research & analysis |
| rag-knowledge-base | Local RAG knowledge base |
| knowledge-graph-memory | Graph-based long-term memory |

</details>

<details>
<summary><b>Automation</b></summary>

| Skill | Description |
|-------|-------------|
| system-control | Screenshots, system info |
| web-scraper | Web content extraction |
| cron-scheduler | Timed task execution |
| workflow | Multi-step automation |
| batch | Bulk task processing |
| email | Email read, search, send (IMAP/SMTP) |
| voice | TTS (edge-tts) + STT (Whisper) |

</details>

<details>
<summary><b>Self-Evolution</b></summary>

| Skill | Description |
|-------|-------------|
| self-improving-agent | Learn from mistakes |
| proactive-agent | Autonomous task discovery |
| effect-tracker | Decision outcome tracking |
| code-review | Automated code review |
| test-runner | Automated testing |

</details>

<details>
<summary><b>Social Media</b></summary>

| Skill | Description |
|-------|-------------|
| xhs-creator | Xiaohongshu content creation |
| xhs-publisher | Xiaohongshu auto-publishing |
| reddit-readonly | Reddit content scraping |

</details>

---

## 📁 Architecture

```
~/.xyvaclaw/
├── openclaw.json          # Main configuration
├── workspace/
│   ├── SOUL.md            # AI personality definition
│   ├── AGENTS.md          # Operating protocols
│   ├── skills/            # 42 skill modules
│   └── memory/            # Persistent memory
├── extensions/
│   ├── feishu/            # 112 TS files — Feishu integration
│   └── lossless-claw/     # Lossless context engine
├── agents/                # Multi-agent configs
└── logs/                  # Runtime logs
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Product Introduction](docs/PRODUCT-INTRODUCTION.md) | Core capabilities & competitive advantages |
| [API Keys Guide](docs/API-KEYS-GUIDE.md) | How to obtain API keys for each provider |
| [Feishu Setup](docs/FEISHU-SETUP.md) | Step-by-step Feishu bot configuration |
| [FAQ](docs/FAQ.md) | Frequently asked questions |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork → Clone → Branch → Code → PR
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd xyvaclaw
git checkout -b feature/your-feature
# Make changes
git push origin feature/your-feature
# Open PR on GitHub
```

---

## 📄 License

[MIT License](LICENSE) — Free for personal and commercial use.

---

## ⭐ Star History

If xyvaClaw helps you, please give it a ⭐! It motivates us to keep improving.

如果 xyvaClaw 对你有帮助，请给个 ⭐ 吧！这是我持续改进的动力。

---

<div align="center">

**xyvaClaw** — *From Claw to xyvaClaw, not a replacement, but an evolution.*

**从 Claw 到 xyvaClaw，不是替代，是进化。**

Made with ❤️ by the xyvaClaw team

</div>
