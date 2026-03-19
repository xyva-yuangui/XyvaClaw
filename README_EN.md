<div align="center">

# 🐾 xyvaClaw

### Your Extended Virtual Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey.svg)]()
[![Node.js](https://img.shields.io/badge/Node.js-22%2B-green.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)]()
[![Skills](https://img.shields.io/badge/Skills-42%2B-orange.svg)]()
[![V5 Pipeline](https://img.shields.io/badge/Cognitive-V5.1-red.svg)]()
[![Feishu](https://img.shields.io/badge/Feishu-Deep%20Integration-purple.svg)]()

**One-click deploy · 5-stage cognitive pipeline · 42+ skills · 4-tier memory · 3-level API fallback · Self-evolving**

[🇨🇳 中文](README.md) · [🇬🇧 English](#-what-is-xyvaclaw) · [📖 Architecture Doc](docs/PRODUCT-ARCHITECTURE_EN.md) · [📖 架构文档](docs/PRODUCT-ARCHITECTURE.md)

**🌐 Website: [www.xyvaclaw.com](https://www.xyvaclaw.com) · Author: 圆规 (Xyva-yuangui)**

**Community: [Discord](https://discord.gg/QABg4Z2Mzu) · [X (Twitter)](https://x.com/dadoudou90) · [QQ Group 1087471835](https://qm.qq.com/q/1087471835)**

</div>

---

## ⚡ Quick Start (30 seconds)

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

> 💡 No git? [Download ZIP](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip), extract, then run `bash xyvaclaw-setup.sh`

<details>
<summary><b>📋 Detailed install steps</b></summary>

### Prerequisites (one-time)

1. **Get an AI model API key** (free signup, pick one):
   - [DeepSeek](https://platform.deepseek.com/api_keys) (recommended, free credits on signup)
   - [Bailian / Tongyi Qianwen](https://bailian.console.aliyun.com/) (Alibaba Cloud, one key for multiple models)

2. **Open a terminal**: macOS `Command + Space` → type `Terminal` | Linux `Ctrl + Alt + T`

### The installer handles everything

- ✅ Detects and installs missing dependencies (Node.js, Python, ffmpeg)
- ✅ Launches a **web-based setup wizard** (enter API key in your browser)
- ✅ Deploys 42+ skills and all configurations
- ✅ Sets up auto-start on boot

### After installation

```bash
xyvaclaw gateway          # Start your AI assistant
# Open http://localhost:18789 in your browser
```

</details>

---

## 🌍 What is xyvaClaw?

xyvaClaw is an **enhanced AI assistant platform** built on the [OpenClaw](https://openclaw.ai/) runtime. It's not just a chatbot — through its **V5 five-stage cognitive pipeline**, it can **understand intent, decompose tasks, reason structurally, self-check quality**, and then respond.

```
User message → Cognitive Pipeline (Understand → Analyze → Reason → QA → Respond) → Execute → Remember → Self-iterate
```

Think of it as **OpenClaw on steroids**: same engine, but with pre-tuned models, battle-tested skills, enterprise-grade Feishu/Lark integration, and an evolution engine that makes your assistant smarter every day.

### Why xyvaClaw?

| | Raw OpenClaw | xyvaClaw |
|---|---|---|
| **Setup** | Manual JSON editing | One-click installer + Web wizard |
| **Cognition** | Direct LLM call | **5-stage pipeline**: intent → plan → reason → QA gate → respond |
| **Models** | BYO | Pre-configured DeepSeek V3.2 + 8-model Bailian pool + custom providers |
| **Resilience** | Single model | **3-level automatic fallback** — zero downtime |
| **Memory** | Basic MEMORY.md | **4-tier**: session → daily → long-term → reasoning store (SQLite) |
| **Reasoning** | Depends on model | **5 structured templates** + adversarial pro/con reasoning |
| **Feishu/Lark** | Basic send/receive | **112 TypeScript source files** covering nearly every API |
| **Skills** | Install one by one | **42 skills pre-installed**, organized by category |
| **Self-Evolution** | ❌ None | ✅ Error tracking → pattern library → rule promotion |
| **Ops** | Manual | Health checks, log rotation, auto-start, cron maintenance |

---

## 🧠 V5 Cognitive Pipeline — Core Engine

Every user message passes through the **V5 Orchestrator**'s five-stage pipeline:

```
┌──────────────────────────────────────────────────────────────────┐
│                        V5 Orchestrator                            │
│                                                                    │
│  ① Message Analysis → ② Task Decomposition → ③ Reasoning Chain   │
│     (required)          (complex tasks)         (reasoning tasks)  │
│                                                                    │
│  → ④ Quality Gate → ⑤ Latency Recording                          │
│     (moderate+)       (automatic)                                  │
└──────────────────────────────────────────────────────────────────┘
```

| Stage | Module | Capability |
|-------|--------|------------|
| **① Understand** | `message-analyzer` | Rule engine (<1ms) + LLM deep analysis: **12 intent categories**, 5 dialogue strategies, 8 emotion tags, auto model routing |
| **② Analyze** | `task-planner` | Complex tasks → DAG decomposition with **parallel execution**, dependencies, critical path |
| **③ Reason** | `multi-step-reasoning` | **5 reasoning templates** (investment/tech selection/plan evaluation/root cause/general), adversarial pro/con reasoning |
| **④ QA Gate** | `thought-quality-gate` | 5-dimension quality check (logic/data/coverage/counter-arguments/actionability), score < 0.6 = redo |
| **⑤ Monitor** | `response-latency-monitor` | P50/P95/P99 latency stats by Provider/Model |

<details>
<summary><b>View message analysis output example</b></summary>

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

## 💾 4-Tier Memory System

```
┌────────────────────────────────────────────────────┐
│  SESSION-STATE.md    ← Current session (WAL)        │
├────────────────────────────────────────────────────┤
│  memory/YYYY-MM-DD.md  ← Daily memories             │
├────────────────────────────────────────────────────┤
│  MEMORY.md          ← Long-term (preferences/rules) │
├────────────────────────────────────────────────────┤
│  .reasoning/SQLite  ← Reasoning store (structured)   │
└────────────────────────────────────────────────────┘
```

| Mechanism | Description |
|-----------|-------------|
| **WAL Protocol** | On correction/preference/decision: **write SESSION-STATE.md BEFORE replying** — context vanishes, files survive |
| **Working Buffer** | Context > 60% → activate danger zone buffer, auto-recover after compaction |
| **Context Compression** | Custom 128K smart compression: **35.7% token savings**, 42.8ms compression time |
| **Alias Expansion** | Auto-expand synonyms before search (`xhs` → `Xiaohongshu/RED/RedNote`) |
| **Self-Learning** | At least 1 learning per day: failures→ERRORS.md, corrections→LEARNINGS.md, rules→AGENTS.md |

---

## 🔀 Model Routing & 3-Level Fallback

### Smart Routing

| Scenario | Recommended Model | Context Window |
|----------|-------------------|----------------|
| Default / Chat | DeepSeek V3.2 | 128K |
| Deep analysis / Reasoning / Code | DeepSeek Reasoner | 128K |
| Image understanding | Qwen3.5+ / Kimi-K2.5 | 1M / 262K |
| Long text / Large context | Qwen3-Max | 262K |

### 3-Level Fallback (Zero Downtime)

```
Tier 1: DeepSeek (5s timeout)  ──fail──→  Tier 2: Qwen3.5+ (15s)  ──fail──→  Tier 3: Kimi-K2.5 (10s)
```

- Millisecond-level timeout detection + seamless switchover
- Automatic health checks every 8 hours
- Supports **custom providers** (any OpenAI-compatible API, with auto model detection)

---

## 🔄 Self-Evolution Engine

```
Error detected → error-tracker.json → auto fix suggestions → verify → learn
                                                                       ↓
Temp memory → Daily memory → Long-term memory → Operating rules (AGENTS.md)
```

| Mechanism | Description |
|-----------|-------------|
| **Error Tracking** | Grouped by category, ≥3 same errors → P0 alert to user |
| **Pattern Library** | Success rate ≥85% → promote to rule; <70% → weak pattern alert |
| **Daily Maintenance** | Iteration report + bootstrap refresh + latency stats + reasoning store summary |
| **Evolution Path** | Temp memory → daily memory → long-term memory → operating rules |

---

## ⚡ 42+ Skills

<details>
<summary><b>🔧 Core (enabled by default)</b></summary>

| Skill | Description |
|-------|-------------|
| claw-shell | Safe shell execution with dangerous command detection |
| error-guard | System control plane: /status, /flush, /recover |
| browser-pilot | Chrome CDP browser automation |
| vision-reader | Image/OCR recognition |
| secret-manager | Secure API key management |
| git | Version control operations |

</details>

<details>
<summary><b>📝 Content Creation</b></summary>

| Skill | Description |
|-------|-------------|
| content-creator | Multi-platform content generation |
| auto-video-creator | AI video creation |
| sora-video | Sora 2 video generation + prompt optimization |
| python-dataviz | Data visualization |
| chart-image | Chart generation |
| excel-xlsx | Excel read/write |
| word-docx | Word document generation |
| pptx-generator | PowerPoint creation |
| pdf-processor | PDF extract, merge, split, convert |
| qwen-image | AI image generation |

</details>

<details>
<summary><b>📊 Data & Quantitative</b></summary>

| Skill | Description |
|-------|-------------|
| quant-strategy-engine | A-share quantitative stock screening, factor analysis, backtesting |
| auto-researcher | Automated research & analysis |
| rag-knowledge-base | Local RAG knowledge base |
| knowledge-graph-memory | Graph-based long-term memory |

</details>

<details>
<summary><b>🤖 Automation</b></summary>

| Skill | Description |
|-------|-------------|
| cron-scheduler | Timed task management (cron) |
| workflow | Multi-step automation pipelines |
| batch | Bulk task processing |
| web-scraper | Web content extraction |
| system-control | Screenshots, system info |
| email | Email read/search/send (IMAP/SMTP) |
| voice | TTS (200+ voices) + STT (Whisper) |

</details>

<details>
<summary><b>🔄 Self-Evolution</b></summary>

| Skill | Description |
|-------|-------------|
| self-improving-agent | Error learning, correction logging, knowledge promotion |
| proactive-agent | WAL, Working Buffer, autonomous task discovery |
| effect-tracker | Skill effect tracking (SQLite) |
| code-review | Automated code review |
| test-runner | Automated testing |

</details>

<details>
<summary><b>💬 Social Media & Communication</b></summary>

| Skill | Description |
|-------|-------------|
| xhs-creator | Xiaohongshu (RED) content creation |
| xhs-publisher | Xiaohongshu auto-publishing |
| smart-messenger | Smart message routing |
| feishu-doc-extended | Advanced Feishu/Lark document operations |
| reddit-readonly | Reddit content scraping |
| miniflux-news | RSS news aggregation |

</details>

---

## 💬 Deep Feishu/Lark Integration

- **112 TypeScript source files** covering nearly every Feishu API
- Messages, documents, spreadsheets, calendar, approvals, drive, wiki
- Enterprise-grade reliability: deduplication, serial scheduling, timeout watchdog, graceful degradation

---

## 🏗 System Architecture

```
┌─────────┐     ┌──────────────┐     ┌───────────────────┐
│  User    │────→│ Feishu/WebChat│────→│  OpenClaw Gateway  │
│  Message │     │  Channels     │     │  (port 18789)      │
└─────────┘     └──────────────┘     └────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼───────┐          ┌──────▼──────┐
              │ Bootstrap  │            │ V5 Orchestrator│          │   Skills    │
              │ Bundle     │            │ Cognitive      │          │  42 Modules │
              │ (SOUL/USER │            │ Pipeline       │          │             │
              │ /TOOLS/... │            │                │          │ quant/xhs/  │
              │  → JSON)   │            │ ① Analysis     │          │ browser/    │
              └────────────┘            │ ② Planning     │          │ video/...   │
                                        │ ③ Reasoning    │          └──────┬──────┘
                                        │ ④ QA Gate      │                 │
                                        │ ⑤ Monitoring   │                 │
                                        └───────┬───────┘                  │
                                                │                          │
                    ┌───────────────────────────┼──────────────────────────┤
                    │                           │                          │
              ┌─────▼─────┐            ┌────────▼────────┐         ┌──────▼──────┐
              │ Memory     │            │  Model Routing   │         │  Effect     │
              │ System     │            │                  │         │  Tracker    │
              │            │            │ DS V3.2 (primary)│         │             │
              │ SESSION    │            │ DS Reasoner      │         │ SQLite      │
              │ MEMORY.md  │            │ Qwen3.5+ (vision)│         │ Exec stats  │
              │ .reasoning │            │ 3-level Fallback │         │ Biz metrics │
              │ /SQLite    │            │                  │         │ Reports     │
              └────────────┘            └─────────────────┘         └─────────────┘
```

### File Structure

```
~/.xyvaclaw/
├── .openclaw/
│   └── openclaw.json          # Gateway main config
├── workspace/
│   ├── SOUL.md                # AI personality definition
│   ├── IDENTITY.md            # AI identity
│   ├── USER.md                # User profile
│   ├── AGENTS.md              # Core operating protocols (V5.1)
│   ├── TOOLS.md               # Tools & environment reference
│   ├── HEARTBEAT.md           # Heartbeat tasks
│   ├── MEMORY.md              # Long-term memory
│   ├── SESSION-STATE.md       # Session state
│   ├── skills/                # 42 skill modules
│   ├── scripts/               # V5 cognitive pipeline scripts
│   ├── memory/                # Daily memories
│   ├── .reasoning/            # Reasoning store (SQLite)
│   ├── .learnings/            # Learning records
│   └── state/                 # Runtime state
├── extensions/
│   ├── feishu/                # 112 TS files — Feishu integration
│   └── lossless-claw/         # Lossless context engine
├── agents/                    # Multi-agent configs
└── logs/                      # Runtime logs
```

---

## 🚀 Advanced Install Options

### Unattended Install (zero interaction)

```bash
# macOS — fully automatic
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'

# Linux — fully automatic
DEEPSEEK_API_KEY=sk-your-key \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | One of these | [DeepSeek API Key](https://platform.deepseek.com/api_keys) |
| `BAILIAN_API_KEY` | required | [Bailian API Key](https://bailian.console.aliyun.com/) |
| `FEISHU_APP_ID` | Optional | Feishu/Lark Bot App ID |
| `FEISHU_APP_SECRET` | Optional | Feishu/Lark Bot App Secret |
| `ASSISTANT_NAME` | Optional | Custom assistant name |

### Requirements

| Requirement | Details |
|-------------|---------|
| **OS** | macOS 12+ or Linux (Ubuntu 22+, Debian 12+, CentOS 8+) |
| **Node.js** | 22+ (auto-installed if missing) |
| **Python** | 3.10+ (auto-installed if missing) |
| **API Key** | At least one: [DeepSeek](https://platform.deepseek.com/api_keys) or [Bailian](https://bailian.console.aliyun.com/) |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [Product Architecture (EN)](docs/PRODUCT-ARCHITECTURE_EN.md) | V5 cognitive pipeline, memory system, model routing — full technical doc |
| [产品架构说明书](docs/PRODUCT-ARCHITECTURE.md) | Complete technical documentation in Chinese |
| [API Keys Guide](docs/API-KEYS-GUIDE.md) | How to obtain API keys for each provider |
| [Feishu Setup](docs/FEISHU-SETUP.md) | Step-by-step Feishu/Lark bot configuration |
| [FAQ](docs/FAQ.md) | Frequently asked questions |

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd XyvaClaw && git checkout -b feature/your-feature
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

---

<div align="center">

**xyvaClaw** — *From Claw to xyvaClaw, not a replacement, but an evolution.*

Made with ❤️ by the xyvaClaw team

</div>
