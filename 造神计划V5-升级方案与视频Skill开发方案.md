# 造神计划 V5 — OpenClaw 大版本升级方案 + 视频 Skill 开发方案

> **编写日期**: 2026-03-15  
> **编写人**: Cascade（基于对 `~/.openclaw` 全量代码遍历分析）  
> **目标**: 为"老贾"（OpenClaw）进行 V5 大版本迭代，同时开发视频生成 Skill

---

# 第一部分：OpenClaw 现状深度分析（7 维度）

## 一、当前架构概览

经过对 `~/.openclaw` 全部文件遍历，当前系统架构如下：

| 模块 | 文件/目录 | 状态 |
|------|----------|------|
| **核心配置** | `openclaw.json` | 运行中，版本 2026.3.8 |
| **身份系统** | `SOUL.md` / `IDENTITY.md` / `USER.md` | V4 已定义 |
| **记忆系统** | `MEMORY.md` + `memory/` + `main.sqlite`(17MB) + `knowledge-graph.sqlite` | 运行中 |
| **推理系统** | `.reasoning/`(117个日志) + `playbooks/reasoning.md` | 活跃 |
| **自我迭代** | `.learnings/` + `state/pattern-library.json` + `state/error-tracker.json` | 运行中 |
| **技能系统** | `skills/`(43个技能) | 53/54 健康 |
| **Agent 矩阵** | `agents/`(main/claude-code/content-creator/quant-analyst/xhs-operator) | 5 个 Agent |
| **Playbooks** | `playbooks/`(9个参考手册) | V4 体系 |
| **脚本库** | `scripts/`(61+个脚本) | 活跃 |
| **模型路由** | DeepSeek(主) + 百炼(备) 共 10 个模型 | 双 Provider |
| **渠道** | 飞书(主) | 单渠道 |
| **上下文压缩** | `context-compressor.py` + `incremental-loader.py` | 已开发，待深度集成 |
| **定时任务** | 26 个 Cron，12 个启用 | 运行中 |
| **插件** | `lossless-claw`(上下文引擎) + `feishu_local` + `kg-memory` | 3 个活跃 |

---

## 二、7 维度深度分析

### 1. 理解能力 — 评分：6.5/10

**现状**：
- ✅ 有 `taskDetection` 关键词路由（文档/代码/推理），可根据任务类型自动切换模型
- ✅ `config/aliases.json` 别名展开（xhs→小红书）
- ✅ `bootstrapMaxChars=16000` 保证启动时注入足够上下文

**问题**：
- ❌ **语义理解停留在关键词匹配层**：`taskDetection` 使用硬编码关键词列表，无法理解隐含意图（如"帮我看看这张图怎么回事"应触发视觉模型，但关键词列表里没有"看看"、"怎么回事"）
- ❌ **多轮对话上下文理解弱**：每次 compaction 后依赖 `SESSION-STATE.md` 恢复，但只保留了"一句话摘要"，丢失了对话的推理链和用户意图演变
- ❌ **缺乏意图层级解析**：用户说"帮我搞定小红书"可能是创建内容、发布、还是分析数据，系统无法区分

**V5 改进方向**：
- 引入 **Intent Classification Layer**（意图分类层），用 LLM 做第一轮意图解析
- Compaction 时保留 **意图链**（Intent Chain），而非仅保留任务摘要
- 支持 **模糊指令解析**：将自然语言映射到具体技能组合

---

### 2. 分析能力 — 评分：7/10

**现状**：
- ✅ 有完整的 7 步分析法（`playbooks/analysis.md`）
- ✅ 数据质量检查清单（新鲜度/完整性/交叉验证/异常值/时间范围）
- ✅ 量化系统有完整的数据分析 pipeline（Tushare + 因子选股 + 策略回测）
- ✅ 置信度标注机制

**问题**：
- ❌ **分析流程依赖人工触发**：7 步分析法需要 Agent 自觉执行，没有强制校验机制
- ❌ **数据分析工具分散**：`python-dataviz`、`quant-strategy-engine`、`excel-xlsx` 各自独立，缺少统一的数据分析编排层
- ❌ **无中间结果缓存**：每次分析都从头开始，相同数据源重复拉取
- ❌ **分析结果无结构化存储**：推理日志存在 `.reasoning/` 但是纯 Markdown，无法被程序化检索

**V5 改进方向**：
- 构建 **Analysis Pipeline Engine**：将 7 步分析法编排为可执行 DAG
- 推理日志结构化存储（JSON/SQLite），支持按主题、时间、置信度检索
- 引入 **数据分析中间层缓存**（Data Cache Layer）

---

### 3. 思考能力 — 评分：6/10

**现状**：
- ✅ 对抗性推理协议（正反推理，V4 新增）
- ✅ VFM 修改前评分机制
- ✅ ADL 反直觉纪律（禁止为聪明加复杂度）

**问题**：
- ❌ **思考深度受限于单次 LLM 调用**：所有"思考"都是在一次 LLM completion 内完成，没有多步思考链
- ❌ **缺乏元认知（Meta-Cognition）**：系统无法评估自己"是否想清楚了"，没有"思考质量自检"机制
- ❌ **规划能力弱**：面对复杂任务（如"帮我做一个完整的量化策略"）缺乏自动分解 → 排序 → 执行的规划引擎
- ❌ **正反推理是"建议"而非"强制"**：对抗性推理协议写在文档中，但没有代码层面的执行保障

**V5 改进方向**：
- 引入 **Multi-Step Reasoning Chain**（多步推理链），类似 Chain-of-Thought 但可跨多次 LLM 调用
- 构建 **Task Planner**（任务规划器），自动将大任务分解为可执行步骤
- 加入 **思考质量门控**（Thought Quality Gate）：在给出最终答案前，强制执行自检 prompt

---

### 4. 推理能力 — 评分：6.5/10

**现状**：
- ✅ 三步推理法（前提→推理→结论）
- ✅ 反事实检验
- ✅ 不确定性传播（推断的前提不能得出事实的结论）
- ✅ 高风险推理触发双模型验证
- ✅ 推理日志（`.reasoning/` 已有 117 条）

**问题**：
- ❌ **推理模型选择过于粗糙**：仅靠关键词"分析/推理/代码/文档"切换 reasoner，但很多需要深度推理的场景没有这些关键词
- ❌ **双模型验证成本高但效果未量化**：没有记录双模型验证实际发现了多少次分歧
- ❌ **缺乏推理模板库**：每次推理都是从零开始，没有复用历史推理模式
- ❌ **推理链不可追溯**：推理日志是独立文件，无法链接回原始对话上下文
- ❌ **DeepSeek Reasoner 的 128K 上下文利用率不足**：已开发压缩算法（节省 35.7%），但集成不够深入

**V5 改进方向**：
- 构建 **Reasoning Template Library**：常见推理场景（投资决策/技术选型/方案评估）预置模板
- 推理链关联对话 ID，支持回溯
- 动态推理深度调节：简单问题 1 步，复杂问题自动升级到多步 + 交叉验证

---

### 5. 自我迭代能力 — 评分：7.5/10（当前最强维度）

**现状**：
- ✅ 闭环迭代流程：发现→记录→修复→验证→学习→规则化
- ✅ 即时学习协议：用户纠错时立即写入 `.learnings/LEARNINGS.md`
- ✅ 模式库 `state/pattern-library.json`，支持直觉匹配
- ✅ VFM 评分防止过度工程
- ✅ LLM-as-Judge 自评模板
- ✅ 错误追踪 `state/error-tracker.json`（35 个错误，修复率 25.7%）
- ✅ 进化目标：每周学习 ≥10 条，推理日志 ≥5/周

**问题**：
- ❌ **错误修复率仅 25.7%**（9/35），大量错误被记录但未修复
- ❌ **重复错误 17 个**：相同问题反复发生，说明修复未触达根因
- ❌ **自我迭代是被动的**：只在错误/纠正发生时学习，没有主动探索改进机会
- ❌ **缺乏 A/B 测试能力**：无法对比两种策略的实际效果
- ❌ **蒸馏频率不够**：每周蒸馏太慢，高频场景应每日蒸馏

**V5 改进方向**：
- 错误修复率目标提升到 70%+，引入自动修复建议生成
- 主动迭代：每日扫描 pattern-library，发现低成功率模式，主动提出改进
- 引入 **Shadow Mode**（影子模式）：对关键决策，同时用两种策略生成结果，对比后选优

---

### 6. 对话沟通能力 — 评分：7/10

**现状**：
- ✅ 人设清晰（老贾，直接务实）
- ✅ 沟通偏好已建模（中文/直接/高效/结构化方案）
- ✅ 飞书集成完善（文本/图片/语音/卡片/文档）
- ✅ 消息格式分流（card/post/text 三类路由）
- ✅ 群聊隔离（被@/能增值/纠错→发言）

**问题**：
- ❌ **单渠道限制**：仅飞书，无 Web UI / API / 微信等多渠道
- ❌ **响应格式不够智能**：格式选择依赖规则，而非根据内容自适应
- ❌ **缺乏对话策略**：面对模糊需求，直接执行而非先澄清
- ❌ **情感理解缺失**：无法识别用户情绪（焦虑/着急/不满）并调整沟通方式
- ❌ **长报告输出体验差**：大段文本直接发送，缺乏分段发送/进度提示

**V5 改进方向**：
- 支持多渠道输出（飞书 + Web Dashboard + API）
- 引入 **对话策略引擎**（Dialogue Strategy Engine）：根据任务复杂度决定是直接执行还是先澄清
- 情绪感知：检测用户语气，自适应调整回复风格
- 长内容渐进式输出：先给摘要，再展开详情

---

### 7. 响应时长 — 评分：5.5/10（最弱维度）

**现状**：
- ✅ `responseWatchdogSec=20`，超时进度提示
- ✅ DeepSeek Chat 作为默认模型（响应快）
- ✅ ETA 动态估算（EWMA α=0.3，上下限 3-120 秒）
- ✅ 上下文压缩算法（节省 35.7% token）

**问题**：
- ❌ **DeepSeek API 超时频繁**（ERR-031，13 次记录），是最高频错误
- ❌ **Bootstrap 阶段太重**：每次会话启动需要读取 SOUL/USER/TOOLS/HEARTBEAT/MEMORY/SESSION-STATE 等 6+ 个文件
- ❌ **Reasoner 模型响应慢**：deepseek-reasoner 用于代码/文档任务时，响应时间显著增加
- ❌ **技能调用链路长**：触发技能 → 读 SKILL.md → 执行脚本 → 返回结果，中间没有预加载
- ❌ **Compaction 时上下文丢失**：compaction 后需要重新读取文件恢复上下文，增加延迟
- ❌ **缺乏响应时长监控仪表盘**：没有系统化的响应时长统计和趋势分析

**V5 改进方向**：
- 实现 **Streaming First**：所有输出优先流式返回
- **预加载高频技能**：根据使用频率预读 SKILL.md
- **Bootstrap 精简**：核心文件合并为单一 JSON，减少文件 I/O
- **API Fallback 优化**：DeepSeek 超时时，毫秒级切换到 Qwen
- 响应时长可观测性：建立 P50/P95/P99 监控指标

---

## 三、综合评分

| 维度 | V4 评分 | V5 目标 | 差距 |
|------|---------|---------|------|
| 理解 | 6.5 | 8.5 | +2.0 |
| 分析 | 7.0 | 8.5 | +1.5 |
| 思考 | 6.0 | 8.0 | +2.0 |
| 推理 | 6.5 | 8.5 | +2.0 |
| 自我迭代 | 7.5 | 9.0 | +1.5 |
| 对话沟通 | 7.0 | 8.5 | +1.5 |
| 响应时长 | 5.5 | 8.0 | +2.5 |
| **综合** | **6.6** | **8.4** | **+1.8** |

---

# 第二部分：市场调研 — 2026 年优秀 AI Agent 方案

## 可融合到 V5 的市场方案

| 方案 | 核心理念 | 可融合点 |
|------|----------|----------|
| **LangGraph** (LangChain) | 有状态多 Agent 图编排，持久化记忆，流式响应 | Task Planner 可借鉴其 DAG 编排思路 |
| **AutoGen** (Microsoft) | 多 Agent 对话协作，代码自动生成 | Shadow Mode 双策略验证可参考其多 Agent 对话模式 |
| **CrewAI** | 角色化多 Agent 团队协作 | 已有 `agent-team-orchestration` 技能，可深化角色分工 |
| **Semantic Kernel** | 语义函数 + 原生函数混合编排 | 意图分类层可借鉴其 Semantic Function 设计 |
| **Atomic Agents** | 原子化 Agent 组合，Schema 驱动 | 技能系统可借鉴其原子化设计，提高可组合性 |
| **Manus/OpenManus** | 全自动 Agent，浏览器/代码/文件全能 | 已有 browser-pilot，可学习其任务自动分解策略 |
| **Claude MCP** | Model Context Protocol，标准化工具接入 | 可作为 V5 技能接入的标准协议 |
| **Reflexion/Self-Refine** | 自我反思 → 重试循环 | 思考质量门控可借鉴其 Reflect-then-Act 模式 |

---

# 第三部分：造神计划 V5 — 开发方案

## 架构升级总览

```
┌─────────────────────────────────────────────────────┐
│                   V5 新增层                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Intent   │  │ Task     │  │ Thought Quality   │ │
│  │ Classify │→│ Planner  │→│ Gate (Self-Check)  │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────┤
│                   V4 已有层（增强）                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Memory   │  │ Reasoning│  │ Self-Evolution     │ │
│  │ (升级)   │  │ (升级)   │  │ (主动+被动)        │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
├─────────────────────────────────────────────────────┤
│                   基础设施层（优化）                    │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐ │
│  │ Bootstrap│  │ Streaming│  │ Observability      │ │
│  │ (精简)   │  │ (优先)   │  │ (全链路监控)       │ │
│  └──────────┘  └──────────┘  └───────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 开发阶段规划

### 阶段 1：基础设施加固（1-2 周）— 解决响应时长

| 任务 | 优先级 | 预估工时 | 描述 |
|------|--------|----------|------|
| Bootstrap 精简 | P0 | 3h | 将 6 个 MD 文件合并为单一 `bootstrap-bundle.json`，减少启动读取次数 |
| API Fallback 升级 | P0 | 4h | 毫秒级超时检测 + 无感切换，DeepSeek → Qwen → Kimi 三级梯度 |
| 高频技能预加载 | P1 | 3h | 根据使用频率 top10 技能，启动时预读 SKILL.md 到内存缓存 |
| 响应时长监控 | P1 | 4h | 在 `state/` 建立 P50/P95/P99 响应时长统计，每日心跳报告 |
| Streaming 输出 | P1 | 3h | 长回复分段流式输出，先摘要后详情 |

### 阶段 2：认知能力升级（2-3 周）— 理解+思考+推理

| 任务 | 优先级 | 预估工时 | 描述 |
|------|--------|----------|------|
| Intent Classification Layer | P0 | 8h | LLM 驱动的意图分类，替代关键词匹配，输出结构化意图 JSON |
| Task Planner | P0 | 10h | 复杂任务自动分解为步骤 DAG，支持依赖关系、并行执行 |
| Thought Quality Gate | P0 | 6h | 给出答案前执行自检 prompt，检查逻辑完整性/数据支撑/是否遗漏 |
| Multi-Step Reasoning | P1 | 8h | 跨多次 LLM 调用的推理链，支持中间结果存储和回溯 |
| Reasoning Template Library | P1 | 5h | 投资决策/技术选型/方案评估等 10+ 常用推理模板 |
| Intent Chain Persistence | P2 | 4h | Compaction 时保留意图演变链，而非仅保留最终状态 |

### 阶段 3：记忆与进化升级（1-2 周）— 自我迭代

| 任务 | 优先级 | 预估工时 | 描述 |
|------|--------|----------|------|
| 推理日志结构化 | P0 | 5h | `.reasoning/` 从 Markdown 迁移到 JSON/SQLite，支持检索 |
| 主动迭代引擎 | P1 | 6h | 每日扫描 pattern-library，低成功率模式主动提出改进建议 |
| 自动修复建议生成 | P1 | 5h | 对 error-tracker 中高频错误，自动生成修复建议 |
| Shadow Mode | P2 | 8h | 关键决策同时用两种策略生成结果，对比后选优 |
| 错误修复闭环 | P1 | 4h | 错误修复率从 25.7% 提升到 70%+，引入自动修复 pipeline |

### 阶段 4：沟通与多通道（2-3 周）— 对话沟通

| 任务 | 优先级 | 预估工时 | 描述 |
|------|--------|----------|------|
| Dialogue Strategy Engine | P1 | 6h | 根据任务复杂度决定直接执行 / 先澄清 / 先确认 |
| 情绪感知模块 | P2 | 4h | 检测用户语气，自适应调整回复风格 |
| Web Dashboard | P2 | 12h | 简单的 Web UI 查看系统状态/记忆/推理日志/技能列表 |
| 长内容渐进式输出 | P1 | 3h | 先摘要 → 用户确认 → 展开详情 |

### 总体排期

| 阶段 | 时间 | 核心交付 |
|------|------|----------|
| 阶段 1 | 第 1-2 周 | 响应时长降低 40%+，API 稳定性提升 |
| 阶段 2 | 第 3-5 周 | 理解/思考/推理能力质变 |
| 阶段 3 | 第 6-7 周 | 自我进化从被动变主动 |
| 阶段 4 | 第 8-10 周 | 沟通体验升级 |
| **总计** | **~10 周** | **综合评分从 6.6 → 8.4** |

---

# 第四部分：视频 Skill 开发方案

## 一、API 测试结果

| API | 端点 | 测试状态 | 备注 |
|-----|------|----------|------|
| 创建视频 | `POST /v1/videos` | ✅ 成功 | 返回 task_id，支持 sora-2-reverse 模型 |
| 创建视频(文件参考图) | `POST /v1/videos` (form-data) | 待测 | 需要 multipart/form-data 上传 |
| 创建视频(Completions格式) | `POST /v1/chat/completions` | 待测 | OpenAI 兼容格式，支持 stream |
| 视频编辑 | `POST /v1/videos/{id}/remix` | 待测 | 需要已完成的视频 ID |
| 获取视频内容 | `GET /v1/videos/{id}/content` | ⚠️ 任务失败时返回错误 | 需任务完成后测试 |
| 获取任务状态 | `GET /v1/videos/{id}` | ⚠️ 权限问题 | 返回 "no access to model" 错误，需排查 |
| 通过视频URL创建角色 | `POST /v1/characters` (url) | ✅ 成功 | 返回角色 ID + 头像 |
| 通过任务ID创建角色 | `POST /v1/characters` (from_task) | 待测 | 需要已完成的视频任务 ID |

### 测试详情

**创建视频（成功）**：
```json
// 请求
POST https://aigc.x-see.cn/v1/videos
{
  "prompt": "海浪拍打沙滩，日落时分，电影感",
  "model": "sora-2-reverse",
  "size": "1280x720",
  "seconds": "5",
  "n": 1
}

// 响应
{
  "id": "task_IYNlPOwFtlGgWnlgwkWsTFFxDNmvtkcI",
  "task_id": "task_IYNlPOwFtlGgWnlgwkWsTFFxDNmvtkcI",
  "object": "video",
  "model": "sora-2-reverse",
  "status": "queued",
  "progress": 0,
  "created_at": 1773586745,
  "seconds": "5",
  "size": "1280x720"
}
```

**创建角色（成功）**：
```json
// 请求
POST https://aigc.x-see.cn/v1/characters
{
  "url": "https://filesystem.site/cdn/20251030/javYrU4etHVFDqg8by7mViTWHlMOZy.mp4",
  "timestamps": "1,3"
}

// 响应
{
  "id": "ch_69b6c90f5fb481918d5e64c6cf0e925c",
  "username": "d06b83080.wingedho",
  "display_name": "Soaring Herdstar",
  "permalink": "https://sora.chatgpt.com/profile/d06b83080.wingedho",
  "profile_picture_url": "https://common-assets.com/az/files/..."
}
```

**已知问题**：
1. `sora-2-pro-reverse` 模型创建任务后状态变为 FAILURE，可能是该模型当前不可用或余额不足
2. `GET /v1/videos/{task_id}` 返回 "no access to model" 错误，可能是 API 端的临时问题或需要特殊的查询参数
3. 需要与 API 提供方确认状态查询端点的正确使用方式

---

## 二、Skill 技术设计

### 基本信息

| 项 | 值 |
|-----|-----|
| 技能名称 | `sora-video` |
| 描述 | AI 视频生成、编辑、角色管理。基于 Sora API 实现文本/图片生视频、视频编辑、角色创建等功能 |
| 版本 | 1.0.0 |
| 依赖 | Python 3.9+, requests |
| API 基础地址 | `https://aigc.x-see.cn` |
| 支持模型 | `sora-2-pro-reverse`, `sora-2-characters`, `sora-2-reverse` |

### 目录结构

```
skills/sora-video/
├── SKILL.md                    # 技能说明文档
├── SKILL-REFERENCE.md          # 详细参考文档
├── scripts/
│   ├── check.py                # 健康检查（--check 接口）
│   ├── sora_video.py           # 主入口脚本
│   ├── sora_api.py             # API 封装层
│   └── utils.py                # 工具函数（轮询、重试等）
├── config/
│   └── default.json            # 默认配置（模型、分辨率、时长等）
├── examples/
│   ├── create_video.sh         # 创建视频示例
│   ├── edit_video.sh           # 编辑视频示例
│   └── create_character.sh     # 创建角色示例
└── output/                     # 视频输出目录
```

### 功能矩阵

| 功能 | 命令 | 模型 | 说明 |
|------|------|------|------|
| 文本生成视频 | `create --prompt "..." --model sora-2-reverse` | sora-2-reverse / sora-2-pro-reverse | 纯文本描述生成视频 |
| 图片生成视频 | `create --prompt "..." --image <path/url/base64>` | sora-2-reverse | 基于参考图生成视频 |
| 文件上传生成 | `create-upload --prompt "..." --file <path>` | sora-2-reverse | 通过 form-data 上传参考图 |
| Completions 格式 | `create-chat --prompt "..." --image <url>` | sora-2-reverse | OpenAI 兼容格式，支持流式 |
| 视频编辑 | `edit --video-id <id> --prompt "..." --model <model>` | 同上 | 基于已有视频进行编辑 |
| 查看任务状态 | `status --task-id <id>` | - | 轮询任务进度 |
| 获取视频内容 | `content --task-id <id>` | - | 获取完成的视频URL/下载 |
| 创建角色(URL) | `character --url <video_url> --timestamps "1,3"` | sora-2-characters | 从视频URL提取角色 |
| 创建角色(任务) | `character --task-id <id> --timestamps "0,3"` | sora-2-characters | 从任务提取角色 |
| 健康检查 | `check` | - | 验证 API 连通性和余额 |

### 核心设计原则

1. **异步轮询 + 超时保护**：创建视频后自动轮询状态，最大重试 60 次 × 10 秒 = 10 分钟
2. **结果自动下载**：视频完成后自动下载到 `output/` 目录
3. **飞书集成**：视频完成后自动通过飞书发送给用户
4. **错误重试**：API 失败自动重试 3 次，指数退避
5. **APIKey 安全**：通过 `secret-manager` 技能管理，不硬编码

### API 封装层设计

```python
# sora_api.py 核心接口
class SoraAPI:
    BASE_URL = "https://aigc.x-see.cn"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def create_video(self, prompt: str, model: str = "sora-2-reverse",
                     size: str = "1280x720", seconds: str = "10",
                     input_reference: str = None, n: int = 1,
                     style: str = None, watermark: bool = False,
                     storyboard: bool = False) -> dict:
        """创建视频任务"""
        
    def create_video_upload(self, prompt: str, file_path: str,
                           model: str = "sora-2-reverse", ...) -> dict:
        """通过文件上传创建视频（form-data）"""
        
    def create_video_chat(self, prompt: str, image_url: str = None,
                         model: str = "sora-2-reverse", stream: bool = True) -> dict:
        """OpenAI Completions 格式创建视频"""
        
    def edit_video(self, video_id: str, prompt: str, model: str,
                   input_reference: str = None) -> dict:
        """编辑已有视频"""
        
    def get_status(self, task_id: str) -> dict:
        """获取任务状态"""
        
    def get_content(self, task_id: str) -> dict:
        """获取视频内容（URL）"""
        
    def create_character_from_url(self, url: str, timestamps: str) -> dict:
        """从视频URL创建角色"""
        
    def create_character_from_task(self, task_id: str, timestamps: str) -> dict:
        """从任务ID创建角色"""
        
    def wait_for_completion(self, task_id: str, 
                           max_retries: int = 60, 
                           interval: int = 10,
                           callback=None) -> dict:
        """轮询等待任务完成"""
```

### 使用方式（SKILL.md 中呈现）

```bash
# 健康检查
python3 scripts/check.py

# 文本生成视频
python3 scripts/sora_video.py create \
  --prompt "一只橘猫在阳光下打哈欠，慢动作，电影感" \
  --model sora-2-reverse \
  --size 1280x720 \
  --seconds 10

# 图片+文本生成视频
python3 scripts/sora_video.py create \
  --prompt "让图片中的人物跳舞" \
  --image "https://example.com/photo.jpg" \
  --model sora-2-reverse

# 本地图片上传生成视频
python3 scripts/sora_video.py create-upload \
  --prompt "让图片动起来" \
  --file /path/to/image.png \
  --model sora-2-reverse

# 编辑视频
python3 scripts/sora_video.py edit \
  --video-id task_xxx \
  --prompt "将画面风格改为动漫风" \
  --model sora-2-reverse

# 查看任务状态
python3 scripts/sora_video.py status --task-id task_xxx

# 获取视频内容（自动下载）
python3 scripts/sora_video.py content --task-id task_xxx --download

# 从视频URL创建角色
python3 scripts/sora_video.py character \
  --url "https://example.com/video.mp4" \
  --timestamps "1,3"

# 从任务创建角色
python3 scripts/sora_video.py character \
  --task-id task_xxx \
  --timestamps "0,3"
```

### 配置文件（config/default.json）

```json
{
  "api_base_url": "https://aigc.x-see.cn",
  "default_model": "sora-2-reverse",
  "available_models": [
    "sora-2-pro-reverse",
    "sora-2-characters",
    "sora-2-reverse"
  ],
  "default_size": "1280x720",
  "default_seconds": "10",
  "default_n": 1,
  "watermark": false,
  "polling": {
    "max_retries": 60,
    "interval_seconds": 10,
    "timeout_seconds": 600
  },
  "retry": {
    "max_attempts": 3,
    "backoff_factor": 2,
    "initial_delay": 1
  },
  "output_dir": "output/video"
}
```

### 与现有系统集成

| 集成点 | 方式 |
|--------|------|
| **secret-manager** | API Key 通过 `secret-manager` 存储和读取 |
| **飞书** | 视频完成后通过飞书发送下载链接或视频文件 |
| **error-guard** | API 错误自动记录到 error-tracker |
| **cron-scheduler** | 支持定时生成视频任务 |
| **workflow** | 可作为工作流节点（如：auto-researcher → content-creator → sora-video） |
| **auto-video-creator** | 可与现有 auto-video-creator 技能互补（本地视频 vs AI 生成） |
| **content-creator** | 内容创作流程中，自动生成配套视频 |

### 开发排期

| 阶段 | 时间 | 交付 |
|------|------|------|
| API 封装层 | 1 天 | `sora_api.py` + 单元测试 |
| 主入口脚本 | 1 天 | `sora_video.py`（全部命令） |
| 健康检查 + 配置 | 0.5 天 | `check.py` + `config/default.json` |
| SKILL.md + 文档 | 0.5 天 | 完整技能文档 |
| 飞书集成 | 0.5 天 | 视频完成自动通知 |
| 端到端测试 | 0.5 天 | 全场景测试 |
| **总计** | **4 天** | 完整可用的视频技能 |

---

# 第五部分：待确认事项

## V5 升级相关

1. **阶段优先级**：是否按建议的 4 阶段顺序执行？还是有特别想先做的模块？
2. **Web Dashboard**：是否需要（工时较大 12h），还是先专注核心能力？
3. **多渠道**：除飞书外，是否有其他渠道需求（微信/Web/API）？
4. **模型预算**：V5 增加了 Intent Classification 等额外 LLM 调用，token 成本是否可接受？

## 视频 Skill 相关

1. **状态查询 API 异常**：`GET /v1/videos/{id}` 返回权限错误，需要确认是否是 API 端临时问题，还是需要特殊权限
2. **sora-2-pro-reverse 模型**：测试时任务状态变为 FAILURE，需确认该模型是否可用、余额是否充足
3. **视频存储**：生成的视频是否需要本地保存？还是仅保留 URL 链接？
4. **使用频率预估**：每天大约生成多少视频？（影响轮询策略和 API 成本）
5. **是否需要批量功能**：一次生成多个视频的场景是否常见？

---

> **请确认以上方案，确认后我将立即开始开发。**
