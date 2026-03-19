# xyvaClaw 能力升级方案（基于完整代码审计）

> 审计时间：2026-03-15  
> 审计范围：38 Skills / 2 Extensions / 配置模板 / 安装脚本 / 全部脚本文件  
> 评估维度：运行性能、任务处理效率、回复速度、用户体验

---

## 一、代码审计发现摘要

### 已具备的能力（无需新增）

| 能力 | 对应模块 | 现状 |
|------|---------|------|
| 自我进化 | self-improving-agent-1.0.11 + effect-tracker + error-guard | ✅ 完整 |
| 主动行为 | proactive-agent-3.1.0 | ✅ 完整 |
| 多 Agent 协作 | agent-team-orchestration | ✅ 有，基础版 |
| 无损上下文 | lossless-claw extension (20 TS files) | ✅ 完整 |
| 四层记忆 | knowledge-graph-memory + MEMORY.md + SESSION-STATE.md | ✅ 完整 |
| 五级容灾 | openclaw.json.template (5 fallback models) | ✅ 完整 |
| 浏览器自动化 | browser-pilot (Playwright) | ✅ 增强版 |
| 文档处理 | word-docx, excel-xlsx | ✅ Word + Excel |
| 视频制作 | auto-video-creator + video-subtitles | ✅ 完整 |
| 图表生成 | chart-image + python-dataviz | ✅ 完整 |
| AI 图片 | qwen-image | ✅ 完整 |
| 股票分析 | quant-strategy-engine | ✅ 完整 |
| 小红书 | xhs-creator + xhs-publisher | ✅ 完整 |
| 飞书 | feishu extension (112 TS files) + feishu-doc-extended | ✅ 最深 |
| Shell | claw-shell (tmux) | ✅ 完整 |
| Web 抓取 | web-scraper (3 个 Python 脚本) | ✅ 完整 |
| 研究 | auto-researcher | ✅ 完整 |
| RAG 知识库 | rag-knowledge-base (ChromaDB + DashScope) | ✅ 完整 |
| 定时任务 | cron-scheduler + cron-mastery | ✅ 完整 |
| 工作流 | workflow + batch | ✅ 完整 |
| Git | git skill | ✅ 完整 |
| 代码审查 | code-review | ✅ 完整 |
| 测试运行 | test-runner | ✅ 完整 |
| 截图发送 | screenshot-sender | ✅ 完整 |
| 系统控制 | system-control | ✅ 完整 |
| 消息发送 | smart-messenger | ✅ 完整 |
| OCR | vision-reader | ✅ 完整 |
| RSS 新闻 | miniflux-news | ✅ 完整 |
| 电商/旅行 | commerce-travel-shopper | ✅ 完整 |
| 内容创作 | content-creator | ✅ 完整 |
| 密钥管理 | secret-manager | ✅ 完整 |
| Reddit | reddit-readonly | ✅ 只读 |
| 效果追踪 | effect-tracker (SQLite + 告警) | ✅ 完整 |

### 结论
你说得对，**之前方案中的大部分"缺失能力"实际上已经存在**。以下是基于真实代码审计后，**真正需要升级的地方**——聚焦于运行性能和用户体验。

---

## 二、性能优化方案（提升回复速度和任务效率）

### 🔴 P0-1: openclaw.json 性能参数调优

**当前问题**：`@/config-base/openclaw.json.template` 中 `bootstrapMaxChars: 5000` 过低，而 `TOOLS.md` 中标注的是 16000。两处不一致。

**影响**：bootstrap 过小会导致 Agent 启动时上下文不足，第一轮回复质量差，需要多轮才能理解任务。

**建议修改**：

```json
{
  "bootstrapMaxChars": 16000,      // 5000 → 16000（与 TOOLS.md 一致）
  "compaction.contextThreshold": 0.70  // 0.65 → 0.70（给更多空间再压缩，减少频繁压缩开销）
}
```

**预期效果**：首轮回复准确度提升，减少"你刚才说的什么？"类追问。

---

### 🔴 P0-2: Skill 按需加载优化

**当前问题**：`@/config-base/config/skill_loading.json` 中 `common_skills` 只列了 3 个（quant-stock-screener, proactive-agent, self-improving-agent），但实际高频使用的还有 browser-pilot、claw-shell、web-scraper 等。

**影响**：非预加载的 Skill 首次调用时有冷启动延迟（~1-3 秒）。

**建议修改**：

```json
{
  "lazy_loading": {
    "enabled": true,
    "common_skills": [
      "proactive-agent",
      "self-improving-agent",
      "claw-shell",
      "browser-pilot",
      "web-scraper",
      "error-guard",
      "effect-tracker",
      "smart-messenger"
    ],
    "other_skills": "on_demand"
  }
}
```

**预期效果**：高频 Skill 零冷启动，用户体验提升明显。

---

### 🔴 P0-3: responseWatchdogSec 超时优化

**当前问题**：`TOOLS.md` 标注 `responseWatchdogSec: 20`，但飞书 channel 配置中是 `15`。当 DeepSeek API 偶尔慢时（高峰期 10-20s），15 秒看门狗会误判超时并中断正在生成的回复。

**建议**：

```json
{
  "channels.feishu.responseWatchdogSec": 30,  // 15 → 30
  "TOOLS.md 中标注的也改成 30"
}
```

**预期效果**：减少 API 高峰期的误超时中断，尤其是深度推理任务。

---

### 🔴 P0-4: 会话超时优化

**当前问题**：`session.resetByType.direct.idleMinutes: 180`（3 小时），`session.reset.idleMinutes: 10080`（7 天）。直接对话 3 小时超时合理，但有些复杂项目任务可能需要更长时间。

**建议**：保持现状，但添加一个 `session.extendOnActivity` 配置：

```json
{
  "session": {
    "resetByType": {
      "direct": {
        "mode": "idle",
        "idleMinutes": 360    // 180 → 360（6 小时，给复杂任务更多时间）
      }
    }
  }
}
```

---

### 🟡 P1-1: claw-shell 输出延迟

**当前问题**：`@/config-base/workspace/skills/claw-shell/handler.js` 中命令执行后 `setTimeout(r, 500)` 固定等待 500ms 再读取输出。对于耗时长的命令（如 npm install、pip install），500ms 读不到完整输出。

**建议**：改为轮询式输出检测：

```javascript
// 替代固定 500ms 等待
async function waitForOutput(maxWaitMs = 5000, intervalMs = 200) {
  let prevOutput = "";
  let stableCount = 0;
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    await new Promise(r => setTimeout(r, intervalMs));
    const output = readOutput();
    if (output === prevOutput) {
      stableCount++;
      if (stableCount >= 2) break;  // 输出稳定，命令可能已完成
    } else {
      stableCount = 0;
      prevOutput = output;
    }
  }
  return readOutput();
}
```

**预期效果**：短命令更快返回（<500ms），长命令等到完整输出再返回。

---

### 🟡 P1-2: browser-pilot SKILL.md 文档自相矛盾

**当前问题**：`@/config-base/workspace/skills/browser-pilot/SKILL.md` 的"增强功能"部分说支持文件上传/下载/多标签页，但"限制"部分又说"不支持高级操作（如文件上传、下载）"和"不支持多标签页"。这个矛盾会误导 AI，导致它不敢使用这些已实现的功能。

**建议**：删除"限制"部分的过时信息，以及"开发计划"中的过时时间线。

---

### 🟡 P1-3: effect-tracker 数据路径不一致

**当前问题**：effect-tracker SKILL.md 中数据路径写的是 `~/.openclaw/logs/`，但 xyvaClaw 的数据目录是 `~/.xyvaclaw/`。如果 effect-tracker 实际代码也硬编码了 `~/.openclaw/`，数据会写到错误的位置。

**建议**：检查并统一所有路径为 `$OPENCLAW_HOME`（即 `~/.xyvaclaw`）。

---

### 🟡 P1-4: miniflux-news 配置路径过时

**当前问题**：`@/config-base/workspace/skills/miniflux-news/scripts/miniflux.py` 中配置路径硬编码为 `~/.config/clawdbot/miniflux-news.json`，使用了旧品牌名 "clawdbot"。

**建议**：改为 `~/.config/xyvaclaw/miniflux-news.json`，同时保留对旧路径的兼容读取。

---

### 🟡 P1-5: Skill 危险命令检测不完整

**当前问题**：`claw-shell/handler.js` 的 `isDangerous()` 只检查 `["sudo", " rm ", " rm-", "reboot", "shutdown", "mkfs", "dd "]`。缺少 `chmod 777`、`> /dev/sda`、`curl | bash`、`:(){ :|:& };:` 等危险模式。

**建议**：扩展危险命令列表并增加正则检测。

---

## 三、功能补齐方案（真正缺失的能力）

经过完整审计，以下是**确认缺失**的功能：

### 🟡 P1-6: PPT 生成（真正缺失）

当前只有 Word (word-docx) 和 Excel (excel-xlsx)，**没有 PPT 生成**。对于"办公三件套"来说这是一个明显缺口。

**建议**：新增 `pptx-generator` Skill，基于 `python-pptx` 库实现。

---

### 🟡 P1-7: PDF 处理（真正缺失）

RAG 知识库声称支持 PDF 解析，但没有独立的 PDF 处理 Skill（提取文本、合并、转换、表格提取等）。

**建议**：新增 `pdf-processor` Skill，基于 `pdfplumber` + `PyPDF2` 实现。

---

### 🟡 P1-8: 语音对话集成（部分缺失）

- edge-tts 已安装（安装脚本 pip3 install edge-tts）
- auto-video-creator 有 `tts_engine.py` 和 `tts_to_opus.py`（TTS 能力存在）
- **但没有语音输入（STT）能力**，也没有在对话流中集成语音

**建议**：新增语音输入（Whisper API 或本地 whisper.cpp），并将 TTS 从视频 Skill 中抽离为独立的 `voice` Skill。

---

### 🟡 P1-9: 邮件收发（真正缺失）

没有邮件相关 Skill。smart-messenger 只支持飞书消息。

**建议**：新增 `email` Skill，基于 `imaplib` + `smtplib` 实现。

---

### 🟢 P2-1: 健康检查 Dashboard

effect-tracker 有数据采集和告警能力，但没有可视化 Dashboard。用户无法直观看到 Skill 运行状态。

**建议**：利用现有 effect-tracker 数据，新增一个简单的 Web Dashboard（复用 setup-wizard 的 Express 框架）。

---

### 🟢 P2-2: 自动更新检查

安装脚本有 post-install 上报，但没有启动时版本检查。

**建议**：在 gateway 启动时检查 GitHub API latest release，提示用户更新。

---

## 四、代码质量问题（影响稳定性）

| 问题 | 文件 | 影响 | 建议 |
|------|------|------|------|
| bootstrapMaxChars 不一致 | openclaw.json.template vs TOOLS.md | 首轮回复质量 | 统一为 16000 |
| browser-pilot 文档矛盾 | browser-pilot/SKILL.md | AI 不敢使用已有功能 | 修正文档 |
| 路径硬编码 ~/.openclaw/ | effect-tracker, miniflux-news 等 | 数据写入错误位置 | 统一用 $OPENCLAW_HOME |
| 旧品牌名 clawdbot | miniflux-news/scripts/miniflux.py | 用户困惑 | 改为 xyvaclaw |
| 危险命令检测不足 | claw-shell/handler.js | 安全风险 | 扩展检测列表 |
| TOOLS.md 参数与实际配置不一致 | TOOLS.md vs openclaw.json.template | 运行行为不可预测 | 以 openclaw.json.template 为准，同步 TOOLS.md |

---

## 五、优先级排序（推荐执行顺序）

### 立即可做（仅配置修改，无风险）

| 序号 | 项目 | 改动量 | 影响 |
|------|------|--------|------|
| 1 | P0-1: bootstrapMaxChars 调优 | 1 行 | 首轮回复质量 |
| 2 | P0-2: common_skills 扩展 | 5 行 | 高频 Skill 零冷启动 |
| 3 | P0-3: watchdog 超时调整 | 2 行 | 减少误超时 |
| 4 | P0-4: 会话超时扩展 | 1 行 | 复杂任务更好体验 |
| 5 | P1-2: browser-pilot 文档修正 | 删 10 行 | AI 正确使用已有功能 |
| 6 | P1-3: 路径统一 | 多处 | 数据不丢失 |
| 7 | P1-4: 品牌名统一 | 1 处 | 一致性 |
| 8 | P1-5: 危险命令检测扩展 | 5 行 | 安全 |
| 9 | TOOLS.md 参数同步 | 3 行 | 行为可预测 |

### 短期可做（需要写新代码）

| 序号 | 项目 | 改动量 | 影响 |
|------|------|--------|------|
| 10 | P1-1: claw-shell 输出轮询 | 20 行 JS | 命令输出更完整 |
| 11 | P1-6: PPT 生成 Skill | 新 Skill | 补齐办公三件套 |
| 12 | P1-7: PDF 处理 Skill | 新 Skill | 高频需求 |
| 13 | P1-8: 语音对话 | 新 Skill | 差异化体验 |
| 14 | P1-9: 邮件 Skill | 新 Skill | 高频需求 |

---

## 六、需要你的决策

### A. 配置调优（1-9）
建议全部执行，都是低风险的配置和文档修正。

> **👉 是否全部执行 1-9？**

### B. 新功能开发（10-14）
选择你想优先实现的：

- [ ] P1-1: claw-shell 输出优化
- [ ] P1-6: PPT 生成
- [ ] P1-7: PDF 处理
- [ ] P1-8: 语音对话
- [ ] P1-9: 邮件收发

> **👉 选择你想做的，我来写代码。**
