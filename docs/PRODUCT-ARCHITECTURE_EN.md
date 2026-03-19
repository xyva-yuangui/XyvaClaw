# xyvaClaw Product Architecture

> Version: V5.1 | Updated: 2026-03-19 | Based on OpenClaw 2026.3.13

---

## 1. System Overview

xyvaClaw is a private AI assistant platform built on the [OpenClaw](https://openclaw.com) runtime. It integrates large language models (LLMs) with 42 pluggable skills, multi-level API failover, structured reasoning chains, and a persistent memory system into a **self-operating, continuously evolving** AI Agent.

### Core Philosophy

```
User Message → Cognitive Pipeline (Understand → Analyze → Reason → QA → Respond) → Execute → Remember → Self-Iterate
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | OpenClaw Gateway (Node.js, local port 18789) |
| Primary Models | DeepSeek V3.2 / Reasoner (primary) + Bailian (8-model pool) + Custom Providers |
| Channels | Feishu/Lark bot, Web Chat |
| Skill Execution | Python 3.14 + Node.js (shell invocation) |
| Storage | Filesystem (Markdown/JSON) + SQLite (reasoning store, effect tracker) |
| Deployment | macOS / Linux single machine, LaunchAgent auto-start |

---

## 2. V5 Cognitive Pipeline

Every user message (except simple greetings) is orchestrated by the **V5 Orchestrator** through 5 stages:

```
┌──────────────────────────────────────────────────────────────────┐
│                        v5-orchestrator.py                          │
│                                                                    │
│  ① Message Analysis → ② Task Decomposition → ③ Reasoning Chain   │
│    (required)           (complex tasks only)    (reasoning tasks)  │
│                                                                    │
│  → ④ Quality Gate → ⑤ Latency Recording                          │
│     (moderate+)       (automatic)                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.1 Message Analysis (Stage 1 — Required)

**Script**: `message-analyzer-v5.py`

Dual-mode operation:
- **Fast rule engine** (no LLM call, < 1ms): 5 hardcoded rules matching greetings, video, quantitative, dangerous operations, Xiaohongshu, and other high-frequency scenarios
- **LLM deep analysis** (via DeepSeek, ~1-3s): single call completes intent classification + dialogue strategy + emotion sensing + model routing

Output structure:

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

**12 Intent Categories**:
content_creation / data_analysis / code_development / document_generation / system_management / information_query / communication / visual_understanding / reasoning_decision / casual_chat / video_generation / workflow_execution

**5 Dialogue Strategies**:
- `execute_directly` — Clear instruction, execute immediately
- `clarify_first` — Ambiguous instruction, clarify first
- `confirm_then_execute` — High-risk operation, confirm before executing
- `progressive_output` — Complex task, summarize first then expand
- `casual_response` — Casual conversation

### 2.2 Task Decomposition (Stage 2 — Complex Tasks Only)

**Script**: `task-planner-v5.py`

**Trigger condition**: `complexity == "complex"` and `action_type == "plan"`

Decomposes complex tasks into a DAG (Directed Acyclic Graph), supporting:
- Step dependencies (`depends_on`)
- Parallel execution markers (`parallel_group`)
- Per-step recommended skills and models
- Risk assessment and verification methods
- Critical path identification

Output example:
```json
{
  "task_summary": "Full quantitative strategy development",
  "estimated_total_minutes": 45,
  "steps": [
    {"id": "step_1", "name": "Data acquisition", "skill": "quant-strategy-engine", "parallel_group": 1},
    {"id": "step_2", "name": "Factor calculation", "depends_on": ["step_1"], "parallel_group": 2},
    {"id": "step_3", "name": "Backtest verification", "depends_on": ["step_2"], "parallel_group": 3}
  ],
  "critical_path": ["step_1", "step_2", "step_3"]
}
```

### 2.3 Multi-Step Reasoning Chain (Stage 3 — Reasoning Tasks)

**Script**: `multi-step-reasoning-v5.py`

**Trigger condition**: `routing.use_reasoning_chain == true`

Provides 5 reasoning templates, each with 3-4 structured reasoning steps:

| Template | Steps | Use Case |
|----------|-------|----------|
| `investment_decision` | Data collection → Multi-angle analysis → Pro/con reasoning | Investment decisions |
| `tech_selection` | Requirements → Solution comparison → Risk assessment → Final recommendation | Technology selection |
| `plan_evaluation` | Understand plan → Strength analysis → Weakness mining → Improvement suggestions | Plan evaluation |
| `root_cause_analysis` | Symptom description → Hypothesis generation → Systematic elimination → Conclusion & fix | Troubleshooting |
| `general_analysis` | Information gathering → Deep analysis → Conclusion summary | General analysis |

Each reasoning step is persisted to the `.reasoning/chains/` directory for backtracking and reuse.

**Adversarial Reasoning Protocol**: For plan evaluation, investment decisions, and technology selection, the system enforces "pro/con reasoning" — one-sided conclusions are prohibited. Output format:
```
### Pro: [Supporting arguments, ≤3 core points]
### Con: [Opposing arguments, ≤3 core risks]
### Conclusion: [Synthesized judgment + confidence level (high/medium/low)]
```

### 2.4 Quality Gate (Stage 4 — Moderate+ Complexity)

**Script**: `thought-quality-gate-v5.py`

**Trigger condition**: `complexity in ("complex", "moderate")` and `action_type != "chat"`

Executes a 5-dimension quality self-check before the Agent delivers its final answer:

| Dimension | Checks |
|-----------|--------|
| Logic Completeness | Are there jumps in the reasoning chain? Are premises-to-conclusions reasonable? |
| Data Support | Are conclusions backed by data/facts? Any signs of fabrication? |
| Coverage | Are key aspects of the user's request missing? |
| Counter-Arguments | Have opposing scenarios and risks been considered? |
| Actionability | Are the suggestions specific and executable? |

Scoring rules:
- `score < 0.6` → **Fail**, must revise before responding
- `score 0.6-0.8` → Pass, with improvement suggestions
- `score > 0.8` → Quality approved

### 2.5 Latency Recording (Stage 5 — Automatic)

**Script**: `response-latency-monitor.py`

Automatically records latency data for every API call, generating P50 / P95 / P99 statistical reports. Grouped by Provider/Model, retaining the last 7 days of records.

---

## 3. Memory System

xyvaClaw's memory is organized in 4 tiers, from short-term to long-term:

```
┌────────────────────────────────────────────────────┐
│  SESSION-STATE.md    ← Current session (active      │
│                        tasks, decisions, context)    │
├────────────────────────────────────────────────────┤
│  memory/YYYY-MM-DD.md  ← Daily memories (events     │
│                          and learnings of the day)   │
├────────────────────────────────────────────────────┤
│  MEMORY.md          ← Long-term memory (user         │
│                       preferences, rules, projects)  │
├────────────────────────────────────────────────────┤
│  .reasoning/reasoning-store.sqlite  ← Reasoning      │
│                       store (structured, SQLite)     │
└────────────────────────────────────────────────────┘
```

### 3.1 WAL Protocol (Write-Ahead Logging)

**Core principle: Write before responding.**

When the Agent discovers corrections, preferences, or decisions, it must write to `SESSION-STATE.md` before replying to the user. The impulse to reply is the enemy — context vanishes during compaction, but files survive.

### 3.2 Working Buffer (Danger Zone Mechanism)

When context usage exceeds 60%, the Working Buffer activates:
1. Clear `memory/working-buffer.md`
2. Append summary of each message to the buffer
3. After compaction, prioritize reading the buffer to restore context

### 3.3 Context Compression Algorithm

Custom 128K context smart compression:
- **Priority weighting system**: User preferences > active tasks > recent decisions > chat
- **Content type detection**: Auto-identifies 10 content types and assigns weights
- **Time decay factor**: Newer content receives higher weight
- Measured metrics: **35.7% token savings**, 42.8ms compression time, 78.2% cache hit rate

### 3.4 Structured Reasoning Store

**Script**: `reasoning-structured-store-v5.py`

Migrated from Markdown logs to SQLite, supporting:
- Search by topic, time, and confidence level
- Each record contains: topic / conclusion / confidence / risk / sources / verification
- WAL mode writes for high-concurrency safety

### 3.5 Memory Retrieval Enhancement

- **Alias expansion**: Check `config/aliases.json` before searching (e.g., `xhs` → `Xiaohongshu/RED/RedNote`)
- **Negation intent detection**: Strip negation words, search core concepts, prioritize warning/risk entries
- **Skip rules**: Simple greetings and pure calculations don't trigger memory retrieval

### 3.6 Self-Learning

Continuous learning loop:
```
Failures     → .learnings/ERRORS.md
Corrections  → .learnings/LEARNINGS.md
Feature requests → .learnings/FEATURE_REQUESTS.md
General rules → Promoted to AGENTS.md / TOOLS.md / MEMORY.md
```

**Mandatory: At least 1 learning per day. Stop learning = stop evolving.**

---

## 4. Model Routing & API Failover

### 4.1 Model Routing Table

| Scenario | Recommended Model | Context Window |
|----------|-------------------|----------------|
| Default / Chat / Short questions | deepseek/deepseek-chat (V3.2) | 128K |
| Deep analysis / Reasoning / Code / Documents | deepseek/deepseek-reasoner (R1) | 128K |
| Image understanding | bailian/qwen3.5-plus or kimi-k2.5 | 1M / 262K |
| Long text / Large context | bailian/qwen3-max-2026-01-23 | 262K |
| Coding assistance | bailian/qwen3-coder-next | 262K |

The V5 pipeline prioritizes the auto-routing suggestion from `routing.suggested_model`.

### 4.2 3-Level API Fallback

**Script**: `api-fallback-v5.py`

```
Tier 1: DeepSeek (timeout 5s)
    ↓ failure
Tier 2: Bailian/Qwen3.5+ (timeout 15s)
    ↓ failure
Tier 3: Bailian/Kimi-K2.5 (timeout 10s)
```

- Millisecond-level timeout detection + seamless switchover
- Automatic health checks every 8 hours (Cron)
- State persisted to `state/api-fallback-v5-state.json`

### 4.3 Custom Provider Support

Via Setup Wizard or manual `.env` configuration:
- Supports any OpenAI-compatible API (e.g., OpenRouter, local Ollama)
- Model IDs via manual input or auto-detection (`/v1/models` endpoint)
- Environment variable format: `CUSTOM_PROVIDER_{i}_NAME/URL/KEY/MODELS`

---

## 5. Skill System

### 5.1 Architecture

42 pluggable skills, each skill is a directory containing `SKILL.md` (documentation) + scripts + configuration.

```
workspace/skills/
├── quant-strategy-engine/     # Quantitative stock screening
├── browser-pilot/             # Browser automation (CDP)
├── smart-messenger/           # Smart message routing
├── sora-video/                # Sora 2 video generation
├── xhs-creator/               # Xiaohongshu content creation
├── xhs-publisher/             # Xiaohongshu auto-publishing
├── knowledge-graph-memory/    # Knowledge graph memory
├── claw-shell/                # Safe shell execution
├── error-guard/               # System-level safety control plane
├── effect-tracker/            # Skill effect tracking
├── ... (42 total)
└── voice/                     # TTS + STT
```

### 5.2 Skill Preloading

**Script**: `skill-preloader-v5.py`

Preloads Top 10 high-frequency skills' `SKILL.md` into memory cache at startup, achieving zero cold-start (< 5ms load time).

Default preloaded: `quant-strategy-engine` / `browser-pilot` / `smart-messenger` / `sora-video` / `auto-video-creator` / `cron-scheduler` / `web-scraper` / `qwen-image` / `xhs-creator` / `excel-xlsx`

Remaining skills load on demand (`on_demand`). Usage statistics dynamically adjust the preload list.

### 5.3 Effect Tracking

**Script/Skill**: `effect-tracker`

SQLite database records each skill invocation's:
- Execution metrics: invocation count, success rate, average/P95 latency, error type distribution
- Business metrics: content quality score, publish success rate, signal accuracy, etc.
- Daily/weekly reports auto-generated, can push to Feishu

### 5.4 Key Skills Reference

| Skill | Function | Trigger |
|-------|----------|---------|
| **quant-strategy-engine** | A-share quantitative stock screening, factor analysis, backtesting | Quant-related instructions |
| **browser-pilot** | Chrome CDP automation, file upload, multi-tab | When browser operation needed |
| **claw-shell** | Safe shell execution, dangerous command detection | When system commands needed |
| **error-guard** | System control plane: /status, /flush, /recover | On system anomalies |
| **self-improving-agent** | Error recording, correction learning, knowledge promotion | Always active |
| **proactive-agent** | WAL, Working Buffer, memory, safety rules | Always active (behavioral layer) |
| **knowledge-graph-memory** | Knowledge graph construction & retrieval | When memory operations needed |
| **sora-video** | Sora 2 video generation + DeepSeek prompt optimization | Video creation instructions |
| **voice** | TTS (200+ voices) + STT (Whisper) | Voice-related instructions |

---

## 6. Boot & Operations

### 6.1 Boot Sequence

```
v5-orchestrator.py --boot
├── ① bootstrap-bundle-generator.py    # Merge SOUL/USER/TOOLS/HEARTBEAT/MEMORY/SESSION-STATE → single JSON
├── ② skill-preloader-v5.py --preload  # Preload Top10 skills into memory
└── ③ api-fallback-v5.py --check       # 3-level API health check
```

After Gateway restart, `BOOT.md` is automatically executed:
1. Restore `SESSION-STATE.md` active tasks
2. Check `memory/working-buffer.md` for unprocessed logs
3. Check `docs/todo.md` for urgent items
4. Run `self-audit.py` health check
5. Notify user of startup status via Feishu

### 6.2 Heartbeat Mechanism

Per heartbeat (< 30s):
1. Read `docs/todo.md` → execute if items exist
2. Scan last 20 lines of `gateway.err.log` → log new errors to error-tracker
3. Reply `HEARTBEAT_OK` if no anomalies

First heartbeat of the day:
- Execute `self-audit.py` + confirm today's memory has been written
- `SESSION-STATE.md` > 24h → cleanup
- Trading days 9:30-15:00 → check stock screening push

### 6.3 Daily Maintenance

```
v5-orchestrator.py --daily
├── ① proactive-iteration-engine-v5.py --daily   # Scan pattern library, generate iteration report
├── ② bootstrap-bundle-generator.py              # Refresh bootstrap bundle
├── ③ response-latency-monitor.py --report       # P50/P95/P99 latency stats
└── ④ reasoning-structured-store-v5.py --stats   # Reasoning store statistics
```

### 6.4 Cron Jobs

| Task | Frequency | Script |
|------|-----------|--------|
| V5 daily maintenance | Daily 0:30 CST | `v5-orchestrator.py --daily` |
| API health check | Every 8 hours | `api-fallback-v5.py --check` |
| Heartbeat check | Continuous | Gateway built-in |
| Quant stock screening push | Trading days 9:30 | `quant-strategy-engine` |

---

## 7. Self-Iteration Mechanism

### 7.1 Error Tracking Closed Loop

```
Error detected → state/error-tracker.json (category + id)
    → Auto fix suggestions (proactive-iteration-engine)
    → Verify fix
    → Update .learnings/ERRORS.md
    → ≥3 same errors → P0 alert to user
```

### 7.2 Pattern Library & Rule Candidates

**Script**: `proactive-iteration-engine-v5.py`

- Scans `state/pattern-library.json` to identify low success rate patterns
- Analyzes `state/error-tracker.json` high-frequency errors, generates fix suggestions
- High success rate patterns (≥85%, ≥5 occurrences) → rule candidates (`rule-candidates.json`)
- Low success rate patterns (<70%) → weak pattern alerts
- Patterns not updated for 30+ days with low confidence → expired cleanup

### 7.3 Evolution Path

```
Temporary memory (SESSION-STATE.md)
    ↓ valuable
Daily memory (memory/YYYY-MM-DD.md)
    ↓ recurring
Long-term memory (MEMORY.md)
    ↓ becomes a rule
Operating protocols (AGENTS.md / TOOLS.md)
```

---

## 8. Safety Mechanisms

### 8.1 Security Boundaries

- **Private data leakage prohibited**
- **Session isolation**: DMs → `user:{id}`, group chats → `chat:{id}`, verify type match before sending
- **Dangerous operation confirmation**: File deletion, sudo, email sending require user confirmation
- **Hard prohibitions**: Delete openclaw.json, modify gateway.auth.token, rm -rf /, ~/.ssh/
- **claw-shell**: Extended dangerous command detection (chmod 777, curl|bash, fork bomb, etc.)

### 8.2 error-guard Control Plane

System-level safety primitives:
- `/status` — Constant-time system health report
- `/flush` — Emergency stop (cancel all tasks, clear queues)
- `/recover` — Safe recovery sequence

Design principles: Main Agent never blocks, event-driven workers, fail-safe recovery first.

---

## 9. Data Flow Overview

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
              │ .reasoning │            │ Kimi-K2.5 (backup)│        │ Biz metrics │
              │ /SQLite    │            │ 3-level Fallback │         │ Reports     │
              └────────────┘            └─────────────────┘         └─────────────┘
```

---

## 10. Configuration Files

| File | Path | Purpose |
|------|------|---------|
| `openclaw.json` | `~/.xyvaclaw/.openclaw/openclaw.json` | Gateway main config (models/channels/plugins/sessions) |
| `SOUL.md` | `workspace/SOUL.md` | AI personality definition |
| `IDENTITY.md` | `workspace/IDENTITY.md` | AI identity |
| `USER.md` | `workspace/USER.md` | User profile |
| `AGENTS.md` | `workspace/AGENTS.md` | Core operating protocols (V5.1) |
| `TOOLS.md` | `workspace/TOOLS.md` | Tools & environment reference |
| `HEARTBEAT.md` | `workspace/HEARTBEAT.md` | Heartbeat task definitions |
| `BOOT.md` | `workspace/BOOT.md` | Boot sequence definition |
| `MEMORY.md` | `workspace/MEMORY.md` | Long-term memory (partitioned index) |
| `aliases.json` | `config/aliases.json` | Domain alias mapping (memory retrieval enhancement) |
| `skill_loading.json` | `config/skill_loading.json` | Skill loading strategy |
| `models.json` | `agents/main/agent/models.json` | Agent-level model override config |

---

## 11. Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| V5.1 | 2026-03-16 | Message Analyzer merge, V5 Orchestrator, Cron cleanup |
| V5.0 | 2026-03-15 | 5-stage cognitive pipeline, Bootstrap Bundle, API Fallback, Reasoning Chain |
| V4.0 | 2026-03-09 | Adversarial reasoning, memory partitioning, context compression |
| v1.1.2 | 2026-03-19 | Setup Wizard custom provider model configuration fix |
| v1.1.1 | 2026-03-16 | Gateway config path fix, meta/wizard/plugins fix |
| v1.1.0 | 2026-03-15 | Performance optimization (bootstrap 16K, watchdog 30s), 4 new skills |
| v1.0.0 | 2026-03-12 | Initial release |
