<div align="center">

# 🐾 xyvaClaw

### Your Extended Virtual Agent — 你的超级 AI 助手

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey.svg)]()
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-green.svg)]()
[![Skills](https://img.shields.io/badge/Skills-38%2B-orange.svg)]()
[![Feishu](https://img.shields.io/badge/Feishu-Deep%20Integration-purple.svg)]()

**One-click deploy. Self-evolving. 38+ skills. 5-level model fallback. Deep Feishu/Lark integration.**

**一键部署。自我进化。38+ 技能。五级模型容灾。飞书深度集成。**

**作者：圆规（Xyva-yuangui）**

**交流讨论：Q群：1087471835**


[English](#-english) · [中文](#-中文) · [Quick Start](#-quick-start) · [Skills](#-skills-38) · [Docs](docs/)

---

<img src="https://raw.githubusercontent.com/xyva-yuangui/XyvaClaw/main/docs/assets/wizard-preview.png" alt="xyvaClaw Setup Wizard" width="700">

</div>

---

## 🌍 English

### What is xyvaClaw?

xyvaClaw is an **enhanced AI assistant platform** built on the [OpenClaw](https://github.com/nicepkg/openclaw) runtime. It transforms a bare AI chatbot into a **thinking, acting, self-improving digital partner** that works alongside you — through your terminal, your browser, or your Feishu/Lark groups.

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
| **Skills** | Install one by one | **38 skills pre-installed**, organized by category |
| **Self-Evolution** | ❌ None | ✅ Error learning + effect tracking + proactive reflection |
| **Reasoning** | Depends on user's model choice | Auto-selects optimal model per task complexity |
| **Ops** | Manual | Health checks, log rotation, auto-start on boot |
| **Docs** | English only | Full Chinese + English documentation |

### Core Capabilities

#### 🧠 Deep Understanding
- **Lossless Context Engine** — Long conversations without information loss
- **4-Tier Memory** — Session → Daily → Long-term → Knowledge Graph
- **Multimodal Input** — Text, images, documents, screenshots
- **Alias System** — Custom name mappings for natural conversation

#### 🔬 Advanced Reasoning
- **Dual-Model Reasoning** — Fast model for daily chat, reasoning model for complex analysis
- **5-Level Fallback** — DeepSeek Chat → Qwen3.5+ → Kimi K2.5 → DeepSeek Reasoner → Qwen3 Max
- **Quantitative Engine** — Built-in A-share stock screening with multi-factor analysis
- **Transparent Reasoning** — Every complex decision is logged and auditable

#### 🔄 Self-Evolution (Unique to xyvaClaw)
- **Error Learning** — Automatically records mistakes, never repeats them
- **Self-Improving Agent** — Continuously analyzes performance and optimizes strategies
- **Effect Tracker** — Tracks outcomes of every decision, forming feedback loops
- **Proactive Agent** — Doesn't wait to be asked — discovers tasks and acts on them
- **Reflection System** — Periodic self-reflection identifying behavioral patterns

**The longer you use it, the smarter it gets.**

#### ⚡ Task Execution
- **38 Built-in Skills** — Browser automation, document processing, video creation, web scraping, system control
- **Shell Execution** — Run terminal commands directly
- **Workflow Engine** — Multi-step automation pipelines
- **Cron Scheduler** — Timed task execution with mastery-level features
- **Batch Processing** — Bulk operations across multiple tasks

#### 💬 Deep Feishu/Lark Integration
112 TypeScript source files covering:

| Module | Capabilities |
|--------|-------------|
| Messaging | Rich text, Markdown cards, interactive cards, streaming replies |
| Documents | Create/edit docs, insert images & tables, batch operations |
| Bitable | Read/write multi-dimensional tables, create views & fields |
| Calendar & Approval | Schedule management, approval workflows, attendance |
| Drive & Wiki | File upload/download, knowledge base management |
| Reliability | Message dedup, serial dispatch, watchdog timeout, graceful degradation |

---

## 🇨🇳 中文

### xyvaClaw 是什么？

xyvaClaw 是基于 [OpenClaw](https://github.com/nicepkg/openclaw) 运行时**深度增强**的 AI 助手平台。它不只是一个聊天机器人——它能**思考、行动、学习、进化**，通过终端、浏览器或飞书群成为你的数字伙伴。

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
- **38 个技能**：浏览器自动化、文档处理、视频制作、网页抓取...
- **定时任务**：自动化日报、数据同步、内容发布
- **工作流引擎**：多步骤自动化流水线

#### 💬 飞书集成 — 用聊天指挥一切
- **112 个 TypeScript 源文件**覆盖飞书几乎所有 API
- 消息、文档、多维表格、日历、审批、云盘、Wiki
- 企业级可靠性：去重、串行调度、超时看门狗、降级回退

---

## 🚀 Quick Start

### Interactive Install (with Web Wizard)

```bash
# macOS
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw && bash xyvaclaw-setup.sh

# Linux
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw && bash xyvaclaw-setup-linux.sh
```

### One-Liner Unattended Install (zero interaction)

```bash
# macOS — fully automatic, no prompts
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'

# Linux — fully automatic, no prompts
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'
```

The `--auto` flag enables **unattended mode** — all prompts are auto-answered with sensible defaults:
- ✅ Missing dependencies installed automatically
- ✅ Existing config merged (not overwritten)
- ✅ API keys injected from environment variables
- ✅ System service registered and started in background

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
4. ✅ Deploy configs, skills (38+), and extensions
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

## 🛠 Skills (38+)

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
│   ├── skills/            # 38 skill modules
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
