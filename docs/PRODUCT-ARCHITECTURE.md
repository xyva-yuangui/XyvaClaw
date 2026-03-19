# xyvaClaw 产品架构说明书

> 版本：V5.1 | 更新日期：2026-03-19 | 基于 OpenClaw 2026.3.13

---

## 一、系统总览

xyvaClaw 是基于 [OpenClaw](https://openclaw.com) 运行时的私有化 AI 助手平台。它将大语言模型（LLM）与 42 个可插拔技能、多级 API 容灾、结构化推理链和持久化记忆系统集成为一个**自主运行、持续进化**的 AI Agent。

### 核心定位

```
用户消息 → 认知管道（理解→分析→推理→质检→响应）→ 行动执行 → 记忆沉淀 → 自我迭代
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 运行时 | OpenClaw Gateway（Node.js，本地 18789 端口） |
| 主模型 | DeepSeek V3.2 / Reasoner（主力）+ 百炼（8 模型池）+ 自定义 Provider |
| 消息通道 | 飞书机器人、Web Chat |
| 技能运行 | Python 3.14 + Node.js（Shell 调用） |
| 存储 | 文件系统（Markdown/JSON）+ SQLite（推理库、效果追踪） |
| 部署 | macOS / Linux 单机，LaunchAgent 自启动 |

---

## 二、认知管道（V5 Pipeline）

每条用户消息（非简单问候）通过 **V5 Orchestrator** 统一编排，经历 5 个阶段：

```
┌─────────────────────────────────────────────────────────┐
│                   v5-orchestrator.py                      │
│                                                           │
│  ① 消息分析 → ② 任务分解 → ③ 推理链 → ④ 质量门控 → ⑤ 延迟记录 │
│  (必选)       (复杂任务)   (推理类)    (中高复杂度)    (自动)    │
└─────────────────────────────────────────────────────────┘
```

### 2.1 消息分析（Stage 1 — 必选）

**脚本**: `message-analyzer-v5.py`

双模式运行：
- **快速规则引擎**（不调 LLM，< 1ms）：5 条硬编码规则匹配问候、视频、量化、危险操作、小红书等高频场景
- **LLM 深度分析**（调 DeepSeek，~1-3s）：一次调用完成意图分类 + 对话策略 + 情绪感知 + 模型路由

输出结构：

```json
{
  "intent": {
    "primary": "data_analysis",       // 12 种意图分类
    "complexity": "complex",           // simple / moderate / complex
    "urgency": "medium"                // low / medium / high
  },
  "strategy": {
    "type": "progressive_output",      // 5 种对话策略
    "risk_level": "low"
  },
  "emotion": {
    "primary": "curious",              // 8 种情绪标签
    "intensity": 0.6,
    "tone_suggestion": "formal"
  },
  "routing": {
    "suggested_model": "deepseek/deepseek-reasoner",
    "suggested_skills": ["quant-strategy-engine"],
    "use_reasoning_chain": true,
    "reasoning_template": "investment_decision"
  },
  "action_type": "plan"               // execute / plan / clarify / chat
}
```

**12 种意图分类**：
content_creation / data_analysis / code_development / document_generation / system_management / information_query / communication / visual_understanding / reasoning_decision / casual_chat / video_generation / workflow_execution

**5 种对话策略**：
- `execute_directly` — 明确指令，直接执行
- `clarify_first` — 指令模糊，先澄清
- `confirm_then_execute` — 高风险操作，先确认
- `progressive_output` — 复杂任务，先摘要再展开
- `casual_response` — 闲聊

### 2.2 任务分解（Stage 2 — 仅复杂任务触发）

**脚本**: `task-planner-v5.py`

**触发条件**: `complexity == "complex"` 且 `action_type == "plan"`

将复杂任务分解为 DAG（有向无环图），支持：
- 步骤依赖关系（`depends_on`）
- 并行执行标记（`parallel_group`）
- 每步推荐技能和模型
- 风险评估和验证方法
- 关键路径识别

输出示例：
```json
{
  "task_summary": "完整量化策略开发",
  "estimated_total_minutes": 45,
  "steps": [
    {"id": "step_1", "name": "数据获取", "skill": "quant-strategy-engine", "parallel_group": 1},
    {"id": "step_2", "name": "因子计算", "depends_on": ["step_1"], "parallel_group": 2},
    {"id": "step_3", "name": "回测验证", "depends_on": ["step_2"], "parallel_group": 3}
  ],
  "critical_path": ["step_1", "step_2", "step_3"]
}
```

### 2.3 多步推理链（Stage 3 — 推理类任务触发）

**脚本**: `multi-step-reasoning-v5.py`

**触发条件**: `routing.use_reasoning_chain == true`

提供 5 种推理模板，每种包含 3-4 步结构化推理：

| 模板 | 步骤 | 适用场景 |
|------|------|----------|
| `investment_decision` | 数据收集 → 多角度分析 → 正反推理 | 投资决策 |
| `tech_selection` | 需求梳理 → 方案对比 → 风险评估 → 最终建议 | 技术选型 |
| `plan_evaluation` | 理解方案 → 优势分析 → 缺陷挖掘 → 改进建议 | 方案评估 |
| `root_cause_analysis` | 现象描述 → 假设生成 → 逐一排查 → 结论修复 | 故障排查 |
| `general_analysis` | 信息收集 → 深度分析 → 结论总结 | 通用分析 |

每步推理结果持久化到 `.reasoning/chains/` 目录，支持回溯和复用。

**对抗性推理协议**：方案评估、投资决策、技术选型场景强制执行"正反推理"，禁止单向结论。输出格式：
```
### 正论: [支持理由，≤3 条]
### 反驳: [反对理由，≤3 条]
### 结论: [综合判断 + 置信度(高/中/低)]
```

### 2.4 质量门控（Stage 4 — 中高复杂度触发）

**脚本**: `thought-quality-gate-v5.py`

**触发条件**: `complexity in ("complex", "moderate")` 且 `action_type != "chat"`

在 Agent 给出最终答案前执行 5 维质量自检：

| 维度 | 检查内容 |
|------|----------|
| 逻辑完整性 | 推理链是否有跳跃？前提到结论是否合理？ |
| 数据支撑 | 结论是否有数据/事实支持？是否有编造嫌疑？ |
| 遗漏检查 | 是否遗漏了用户需求的关键方面？ |
| 反面考虑 | 是否考虑了反面情况和风险？ |
| 可操作性 | 给出的建议是否具体可执行？ |

评分规则：
- `score < 0.6` → **不通过**，必须改进后重新回答
- `score 0.6-0.8` → 通过，附带改进建议
- `score > 0.8` → 质量合格

### 2.5 延迟记录（Stage 5 — 自动）

**脚本**: `response-latency-monitor.py`

自动记录每次 API 调用的延迟数据，生成 P50 / P95 / P99 统计报告。按 Provider/Model 分组，保留近 7 天记录。

---

## 三、记忆系统

xyvaClaw 的记忆分为 4 层，从短期到长期：

```
┌────────────────────────────────────────────┐
│            SESSION-STATE.md                 │  ← 当前会话（活跃任务、决策、上下文）
├────────────────────────────────────────────┤
│          memory/YYYY-MM-DD.md              │  ← 每日记忆（当天重要事件和学习）
├────────────────────────────────────────────┤
│             MEMORY.md                       │  ← 长期记忆（用户偏好、核心规则、活跃项目）
├────────────────────────────────────────────┤
│       .reasoning/reasoning-store.sqlite    │  ← 推理库（结构化推理日志，SQLite）
└────────────────────────────────────────────┘
```

### 3.1 WAL 协议（Write-Ahead Logging）

**核心原则：先写再回复。**

Agent 发现修正、偏好、决策时，必须先写入 `SESSION-STATE.md`，然后才回复用户。回复冲动是敌人——上下文会因 compaction 消失，但文件会存活。

### 3.2 Working Buffer（危险区机制）

当上下文使用超过 60%，启动 Working Buffer：
1. 清空 `memory/working-buffer.md`
2. 每条消息追加摘要到 buffer
3. Compaction 后优先读取 buffer 恢复上下文

### 3.3 上下文压缩算法

自研 128K 上下文智能压缩：
- **优先级权重系统**：用户偏好 > 活跃任务 > 最近决策 > 闲聊
- **内容类型检测**：自动识别 10 种内容类型并分配权重
- **时间衰减因子**：越新的内容权重越高
- 实测指标：**35.7% token 节省**，42.8ms 压缩时间，78.2% 缓存命中率

### 3.4 推理结构化存储

**脚本**: `reasoning-structured-store-v5.py`

从 Markdown 日志迁移到 SQLite，支持：
- 按主题、时间、置信度检索
- 每条记录包含：topic / conclusion / confidence / risk / sources / verification
- WAL 模式写入，高并发安全

### 3.5 记忆检索增强

- **别名展开**：搜索前查 `config/aliases.json`（如 `xhs` → `小红书/RED/RedNote`）
- **否定意图检测**：去否定词搜核心概念，优先返回警告/风险条目
- **跳过规则**：简单问候、纯计算不触发记忆检索

### 3.6 自我学习

持续学习循环：
```
失败 → .learnings/ERRORS.md
纠正 → .learnings/LEARNINGS.md
功能请求 → .learnings/FEATURE_REQUESTS.md
通用规则 → 提升到 AGENTS.md / TOOLS.md / MEMORY.md
```

**强制要求：每天至少 1 条学习。停止学习 = 停止进化。**

---

## 四、模型路由与 API 容灾

### 4.1 模型路由表

| 场景 | 推荐模型 | 上下文窗口 |
|------|----------|------------|
| 默认 / 闲聊 / 短问题 | deepseek/deepseek-chat (V3.2) | 128K |
| 深度分析 / 推理 / 代码 / 文档 | deepseek/deepseek-reasoner (R1) | 128K |
| 图片理解 | bailian/qwen3.5-plus 或 kimi-k2.5 | 1M / 262K |
| 长文本 / 大上下文 | bailian/qwen3-max-2026-01-23 | 262K |
| 编码辅助 | bailian/qwen3-coder-next | 262K |

V5 管道优先使用 `routing.suggested_model` 的自动路由建议。

### 4.2 三级 API Fallback

**脚本**: `api-fallback-v5.py`

```
Tier 1: DeepSeek (timeout 5s)
    ↓ 失败
Tier 2: 百炼/Qwen3.5+ (timeout 15s)
    ↓ 失败
Tier 3: 百炼/Kimi-K2.5 (timeout 10s)
```

- 毫秒级超时检测 + 无感切换
- 每 8 小时自动健康检查（Cron）
- 状态持久化到 `state/api-fallback-v5-state.json`

### 4.3 自定义 Provider 支持

通过 Setup Wizard 或手动 `.env` 配置：
- 支持任何 OpenAI 兼容 API（如 OpenRouter、本地 Ollama）
- 模型 ID 手动输入或自动检测（`/v1/models` 端点）
- 环境变量格式：`CUSTOM_PROVIDER_{i}_NAME/URL/KEY/MODELS`

---

## 五、技能系统

### 5.1 架构

42 个可插拔技能，每个技能是一个目录，包含 `SKILL.md`（说明）+ 脚本 + 配置。

```
workspace/skills/
├── quant-strategy-engine/     # 量化选股
├── browser-pilot/             # 浏览器自动化（CDP）
├── smart-messenger/           # 智能消息路由
├── sora-video/                # Sora 2 视频生成
├── xhs-creator/               # 小红书内容创作
├── xhs-publisher/             # 小红书自动发布
├── knowledge-graph-memory/    # 知识图谱记忆
├── claw-shell/                # 安全 Shell 执行
├── error-guard/               # 系统级安全控制面
├── effect-tracker/            # 技能效果追踪
├── ... (共 42 个)
└── voice/                     # TTS + STT
```

### 5.2 技能预加载

**脚本**: `skill-preloader-v5.py`

启动时预读 Top 10 高频技能的 `SKILL.md` 到内存缓存，实现零冷启动（< 5ms 加载）。

默认预加载：`quant-strategy-engine` / `browser-pilot` / `smart-messenger` / `sora-video` / `auto-video-creator` / `cron-scheduler` / `web-scraper` / `qwen-image` / `xhs-creator` / `excel-xlsx`

其余技能按需加载（`on_demand`）。使用统计动态调整预加载列表。

### 5.3 效果追踪

**脚本/技能**: `effect-tracker`

SQLite 数据库记录每次技能调用的：
- 执行指标：调用次数、成功率、平均/P95 耗时、错误类型分布
- 业务指标：内容质量评分、发布成功率、信号准确率等
- 日报 / 周报自动生成，可推送飞书

### 5.4 关键技能说明

| 技能 | 功能 | 触发方式 |
|------|------|----------|
| **quant-strategy-engine** | A 股量化选股、因子分析、策略回测 | 量化相关指令 |
| **browser-pilot** | Chrome CDP 自动化，支持文件上传和多标签 | 需浏览器操作时 |
| **claw-shell** | 安全 Shell 执行，危险命令检测 | 需执行系统命令时 |
| **error-guard** | 系统控制面：/status、/flush、/recover | 系统异常时 |
| **self-improving-agent** | 错误记录、纠正学习、知识提升 | 始终活跃 |
| **proactive-agent** | WAL、Working Buffer、记忆、安全规则 | 始终活跃（行为层） |
| **knowledge-graph-memory** | 知识图谱构建与检索 | 需记忆操作时 |
| **sora-video** | Sora 2 视频生成 + DeepSeek 提示词优化 | 视频创作指令 |
| **voice** | TTS（200+ 语音）+ STT（Whisper） | 语音相关指令 |

---

## 六、启动与运维流程

### 6.1 Boot 序列

```
v5-orchestrator.py --boot
├── ① bootstrap-bundle-generator.py    # 合并 SOUL/USER/TOOLS/HEARTBEAT/MEMORY/SESSION-STATE → 单一 JSON
├── ② skill-preloader-v5.py --preload  # 预加载 Top10 技能到内存
└── ③ api-fallback-v5.py --check       # 三级 API 健康检查
```

Gateway 重启后自动执行 `BOOT.md`：
1. 恢复 `SESSION-STATE.md` 活跃任务
2. 检查 `memory/working-buffer.md` 未处理日志
3. 检查 `docs/todo.md` 紧急待办
4. 运行 `self-audit.py` 健康检查
5. 飞书通知用户启动状态

### 6.2 心跳机制

每次心跳（< 30s）：
1. 读 `docs/todo.md` → 有项就执行
2. 扫 `gateway.err.log` 最近 20 行 → 新错误记 error-tracker
3. 无异常回复 `HEARTBEAT_OK`

每日首次心跳：
- 执行 `self-audit.py` + 确认当日 memory 已写
- `SESSION-STATE.md` > 24h → 清理
- 交易日 9:30-15:00 → 检查选股推送

### 6.3 每日维护

```
v5-orchestrator.py --daily
├── ① proactive-iteration-engine-v5.py --daily   # 扫描模式库，生成迭代报告
├── ② bootstrap-bundle-generator.py              # 刷新 bootstrap bundle
├── ③ response-latency-monitor.py --report       # P50/P95/P99 延迟统计
└── ④ reasoning-structured-store-v5.py --stats   # 推理库统计
```

### 6.4 Cron 定时任务

| 任务 | 频率 | 脚本 |
|------|------|------|
| V5 每日维护 | 每天 0:30 CST | `v5-orchestrator.py --daily` |
| API 健康检查 | 每 8 小时 | `api-fallback-v5.py --check` |
| 心跳检查 | 持续 | Gateway 内置 |
| 量化选股推送 | 交易日 9:30 | `quant-strategy-engine` |

---

## 七、自我迭代机制

### 7.1 错误追踪闭环

```
发现错误 → state/error-tracker.json（category + id）
    → 自动修复建议（proactive-iteration-engine）
    → 验证修复
    → 更新 .learnings/ERRORS.md
    → ≥3 次同错 → P0 通知用户
```

### 7.2 模式库与规则候选

**脚本**: `proactive-iteration-engine-v5.py`

- 扫描 `state/pattern-library.json`，识别低成功率模式
- 分析 `state/error-tracker.json` 高频错误，生成修复建议
- 高成功率模式（≥85%，≥5 次）→ 规则候选（`rule-candidates.json`）
- 低成功率模式（<70%）→ 弱模式告警
- 超过 30 天未更新的低置信度模式 → 过期清理

### 7.3 进化路径

```
临时记忆（SESSION-STATE.md）
    ↓ 有价值
每日记忆（memory/YYYY-MM-DD.md）
    ↓ 反复出现
长期记忆（MEMORY.md）
    ↓ 成为规则
操作规范（AGENTS.md / TOOLS.md）
```

---

## 八、安全机制

### 8.1 安全边界

- **禁止泄露私人数据**
- **会话隔离**：私信 → `user:{id}`，群聊 → `chat:{id}`，发送前校验类型匹配
- **危险操作确认**：删文件、sudo、发邮件必须用户确认
- **硬禁止**：删 openclaw.json、改 gateway.auth.token、rm -rf /、~/.ssh/
- **claw-shell**：扩展危险命令检测（chmod 777、curl|bash、fork bomb 等）

### 8.2 error-guard 控制面

系统级安全原语：
- `/status` — 常量时间系统健康报告
- `/flush` — 紧急停止（取消所有任务、清空队列）
- `/recover` — 安全恢复序列

设计原则：主 Agent 永不阻塞，事件驱动，失败安全优先。

---

## 九、数据流全景

```
┌─────────┐     ┌──────────────┐     ┌───────────────────┐
│  用户    │────→│  飞书/WebChat │────→│  OpenClaw Gateway  │
│  消息    │     │  消息通道     │     │  (port 18789)      │
└─────────┘     └──────────────┘     └────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
              ┌─────▼─────┐            ┌───────▼───────┐          ┌──────▼──────┐
              │ Bootstrap  │            │ V5 Orchestrator│          │   Skills    │
              │ Bundle     │            │ 认知管道       │          │  42 个技能  │
              │ (SOUL/USER │            │                │          │             │
              │ /TOOLS/... │            │ ① 消息分析     │          │ quant/xhs/  │
              │  → JSON)   │            │ ② 任务分解     │          │ browser/    │
              └────────────┘            │ ③ 推理链       │          │ video/...   │
                                        │ ④ 质量门控     │          └──────┬──────┘
                                        │ ⑤ 延迟记录     │                 │
                                        └───────┬───────┘                 │
                                                │                         │
                    ┌───────────────────────────┼─────────────────────────┤
                    │                           │                         │
              ┌─────▼─────┐            ┌────────▼────────┐        ┌──────▼──────┐
              │ 记忆系统   │            │   模型路由       │        │  效果追踪   │
              │            │            │                  │        │             │
              │ SESSION    │            │ DS V3.2 (主力)   │        │ SQLite      │
              │ MEMORY.md  │            │ DS Reasoner      │        │ 执行指标    │
              │ .reasoning │            │ Qwen3.5+ (图片)  │        │ 业务指标    │
              │ /SQLite    │            │ Kimi-K2.5 (备)   │        │ 周报/月报   │
              └────────────┘            │ 3级 Fallback     │        └─────────────┘
                                        └─────────────────┘
```

---

## 十、配置文件清单

| 文件 | 路径 | 作用 |
|------|------|------|
| `openclaw.json` | `~/.xyvaclaw/.openclaw/openclaw.json` | Gateway 主配置（模型/通道/插件/会话） |
| `SOUL.md` | `workspace/SOUL.md` | AI 人格定义 |
| `IDENTITY.md` | `workspace/IDENTITY.md` | AI 身份（名字：老贾） |
| `USER.md` | `workspace/USER.md` | 用户画像（名字：圆规） |
| `AGENTS.md` | `workspace/AGENTS.md` | 核心操作规范（V5.1） |
| `TOOLS.md` | `workspace/TOOLS.md` | 工具和环境速查 |
| `HEARTBEAT.md` | `workspace/HEARTBEAT.md` | 心跳任务定义 |
| `BOOT.md` | `workspace/BOOT.md` | 启动序列定义 |
| `MEMORY.md` | `workspace/MEMORY.md` | 长期记忆（分区索引） |
| `aliases.json` | `config/aliases.json` | 领域别名映射（记忆检索增强） |
| `skill_loading.json` | `config/skill_loading.json` | 技能加载策略 |
| `models.json` | `agents/main/agent/models.json` | Agent 级模型覆盖配置 |

---

## 十一、版本历史

| 版本 | 日期 | 核心变更 |
|------|------|----------|
| V5.1 | 2026-03-16 | Message Analyzer 合并、V5 Orchestrator、Cron 清理 |
| V5.0 | 2026-03-15 | 五阶段认知管道、Bootstrap Bundle、API Fallback、推理链 |
| V4.0 | 2026-03-09 | 对抗性推理、记忆分区、上下文压缩 |
| v1.1.2 | 2026-03-19 | Setup Wizard 自定义 Provider 模型配置修复 |
| v1.1.1 | 2026-03-16 | Gateway 配置路径修复、meta/wizard/plugins 修复 |
| v1.1.0 | 2026-03-15 | 性能优化（bootstrap 16K、watchdog 30s）、4 个新技能 |
| v1.0.0 | 2026-03-12 | 初始发布 |
