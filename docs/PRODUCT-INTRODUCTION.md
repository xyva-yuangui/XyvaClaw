# xyvaClaw — 重新定义你的 AI 助手

> 不只是聊天机器人，是能思考、能行动、能进化的私人 AI 伙伴

---

## 一句话介绍

**xyvaClaw** 是基于 OpenClaw 运行时深度增强的 AI 助手平台。它保留了 OpenClaw 的全部基础能力，同时在理解力、推理力、自我进化、任务执行和用户体验上做了系统级的升级。一键部署，开箱即用。

---

## 核心能力矩阵

### 🧠 深度理解 — 不只是听懂，是真的懂

| 能力 | 说明 |
|------|------|
| **无损上下文引擎** | 内置 Lossless-Claw 引擎，对话再长也不会"忘事"。原生 OpenClaw 在长对话中会压缩上下文导致信息丢失，xyvaClaw 通过增量摘要 + 智能裁剪保留关键细节 |
| **多层记忆系统** | 会话记忆（SESSION-STATE.md）→ 日记忆（memory/YYYY-MM-DD.md）→ 长期记忆（MEMORY.md）→ 知识图谱（knowledge-graph-memory），四层递进，像人类一样建立长期认知 |
| **别名理解** | 用户说"老K"，助手知道是指"某个技术文档"——支持自定义别名映射，让对话更自然 |
| **否定意图识别** | "别用那个方案"——能正确理解否定语义，不会误操作 |
| **多模态输入** | 文字、图片、文档、截图，都能理解。qwen3.5-plus 支持图片输入，vision-reader 支持 OCR |

### 🔬 深度推理 — 不只是回答，是深度分析

| 能力 | 说明 |
|------|------|
| **双模型推理** | 日常对话用 DeepSeek V3.2（快速准确），复杂问题自动切换 DeepSeek Reasoner / qwen3-max（深度推理），**你不需要手动选模型** |
| **5级 Fallback** | deepseek-chat → qwen3.5-plus → kimi-k2.5 → deepseek-reasoner → qwen3-max，任何一个模型故障都不影响服务 |
| **推理过程透明** | .reasoning 目录记录每次复杂推理的思考过程，可回溯、可审计 |
| **量化策略引擎** | 内置 A 股量化选股引擎（quant-strategy-engine），多因子筛选、技术指标、财务分析一体化 |

### 🔄 自我进化 — 不只是工具，是会学习的伙伴

这是 **xyvaClaw 与原生 OpenClaw 最大的差异**。

| 能力 | 说明 |
|------|------|
| **错误学习** | 每次犯错自动记录到 `.learnings/ERRORS.md`，下次遇到同类问题直接规避 |
| **自我改进代理** | self-improving-agent 技能持续分析自己的表现，主动优化回答策略 |
| **效果追踪** | effect-tracker 追踪每个决策和行动的结果，形成正反馈循环 |
| **主动行动** | proactive-agent 不等你问——主动发现待办、提醒风险、执行日常任务 |
| **反思机制** | `.reflections/` 目录存储周期性自我反思，识别行为模式和改进方向 |
| **纠错闭环** | 用户纠正 → 记录到 `.learnings/LEARNINGS.md` → 更新行为规则 → 永不再犯 |

**简单说：用得越久，它越懂你，越好用。**

### ⚡ 任务执行 — 不只是建议，是直接帮你干

| 能力 | 说明 |
|------|------|
| **38 个内置技能** | 浏览器自动化、文档处理、视频制作、网页抓取、系统控制... 不需要额外安装 |
| **Shell 执行** | 直接在终端执行命令，安装软件、管理文件、运行脚本 |
| **浏览器自动化** | browser-pilot 控制 Chrome 完成网页操作、表单填写、数据抓取 |
| **定时任务** | cron-scheduler + cron-mastery 管理定时任务，每日报告、数据同步、自动发布 |
| **批量处理** | batch + workflow 引擎支持多步骤自动化流水线 |
| **文档全家桶** | Excel 读写、Word 生成、飞书文档（含图片和表格）、Python 可视化图表 |

### 💬 飞书深度集成 — 不只是机器人，是团队成员

这是 xyvaClaw 的**杀手级特性**。原生 OpenClaw 的飞书支持是基础的消息收发，xyvaClaw 的飞书扩展包含 **112 个 TypeScript 源文件**，覆盖了飞书几乎所有 API：

| 模块 | 文件数 | 能力 |
|------|--------|------|
| 消息与对话 | 15+ | 富文本消息、Markdown 卡片、消息卡片交互、流式回复 |
| 文档操作 | 20+ | 创建/编辑飞书文档、插入图片和表格、批量写入 |
| 多维表格 | 5+ | 读写多维表格（Bitable）、创建视图和字段 |
| 日历与审批 | 8+ | 日程管理、审批流程、考勤查询 |
| 云盘与Wiki | 10+ | 文件上传下载、知识库管理 |
| 权限管理 | 5+ | 文档权限、群组管理、用户目录 |
| 账号体系 | 5+ | 多账号配置、配置 Schema 验证 |
| 可靠性 | 10+ | 消息去重、会话串行调度、看门狗超时、降级回退 |

**用飞书群就能指挥你的 AI 助手完成几乎任何工作。**

---

## 与原生 OpenClaw 对比

| 维度 | 原生 OpenClaw | xyvaClaw |
|------|-------------|----------|
| **安装** | 手动配置 JSON，需要理解 schema | 一键安装 + Web 配置向导 |
| **模型** | 需要自己添加模型定义 | 预配置 10+ 模型，DeepSeek + 百炼双引擎 |
| **Fallback** | 单模型 | 5 级自动 Fallback，零宕机 |
| **上下文** | 原生压缩（会丢信息） | Lossless-Claw 无损引擎 |
| **记忆** | 基础 MEMORY.md | 四层记忆 + 知识图谱 |
| **飞书** | 基础消息收发 | 112 个 TS 文件，覆盖全部 API |
| **技能** | 需要逐个安装 | 38 个技能预装 |
| **自我进化** | 无 | 错误学习 + 效果追踪 + 主动反思 |
| **推理** | 取决于用户选模型 | 自动选择最佳推理模型 |
| **文档** | 英文文档为主 | 中英文完整文档 + API Key 获取教程 |
| **运维** | 手动管理 | 健康检查 + 日志轮转 + 开机自启 |

---

## 技能分层

### 🟢 核心技能（默认安装）
- **secret-manager** — 密钥安全管理
- **claw-shell** — 终端命令执行
- **error-guard** — 错误自动防护
- **vision-reader** — 图片/OCR 识别
- **browser-pilot** — 浏览器自动化
- **git** — 版本控制

### 🔵 内容与文档
- content-creator / auto-video-creator / python-dataviz / chart-image
- excel-xlsx / word-docx / feishu-doc-extended

### 🟡 数据与研究
- quant-strategy-engine（量化选股）/ auto-researcher / rag-knowledge-base / knowledge-graph-memory

### 🟠 自动化与系统
- system-control / web-scraper / cron-scheduler / workflow / batch / screenshot-sender

### 🔴 自我进化
- self-improving-agent / proactive-agent / effect-tracker / code-review / test-runner

### 🟣 社交媒体
- xhs-creator / xhs-publisher / reddit-readonly / miniflux-news

---

## 适合谁？

- **独立开发者** — 让 AI 助手帮你写代码、做研究、管理项目
- **内容创作者** — 自动化内容生成、多平台发布
- **量化交易者** — A 股数据分析、策略回测
- **团队管理者** — 通过飞书群管理团队任务、生成报告
- **AI 爱好者** — 探索 AI 助手的边界，让它真正成为你的伙伴

---

## 为什么叫 xyvaClaw？

**xyva** = eXtended Your Virtual Agent
**Claw** = 致敬 OpenClaw 生态

> 从 Claw 到 xyvaClaw，不是替代，是进化。

---

## 一键开始

```bash
git clone https://github.com/yourname/xyvaclaw.git
cd xyvaclaw
bash xyvaclaw-setup.sh
```

两分钟后，你的 AI 助手就准备好了。

---

*xyvaClaw v1.0.0 — Built with passion, powered by OpenClaw.*
