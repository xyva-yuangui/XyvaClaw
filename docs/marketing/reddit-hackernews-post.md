# Reddit & Hacker News 发帖指南

---

## 一、Reddit

### 发布到哪些 subreddit

| Subreddit | 成员数 | 帖子风格 | 标题建议 |
|-----------|--------|---------|---------|
| r/selfhosted | 350K+ | 技术向，喜欢自建方案 | "xyvaClaw — self-evolving AI assistant with 38+ skills, one-click deploy (open source)" |
| r/LocalLLaMA | 200K+ | 本地 AI 爱好者 | "Built an AI assistant platform with self-evolution, lossless context, and 5-level model fallback" |
| r/OpenAI | 800K+ | AI 讨论 | "Open source alternative: xyvaClaw — AI assistant that learns from mistakes (38 skills, Feishu integration)" |
| r/artificial | 400K+ | AI 通用讨论 | "Show Reddit: xyvaClaw — a self-evolving AI assistant platform (open source)" |

### r/selfhosted 帖子内容（最推荐）

**标题**: xyvaClaw — self-evolving AI assistant with 38+ skills, one-click deploy, deep Feishu/Lark integration (open source, MIT)

**正文**:
```
I've been building xyvaClaw for the past 6 months — it's an enhanced AI assistant platform built on the OpenClaw runtime.

**What it does:**
- 38 pre-installed skills: browser automation, document generation (Word/Excel), video creation, stock screening, web scraping, social media automation
- Self-evolution engine: learns from mistakes, tracks decision outcomes, periodic self-reflection
- Lossless context: long conversations without information loss (custom engine)
- 5-level model fallback: DeepSeek → Qwen → Kimi → Reasoner → Qwen Max (zero downtime)
- 4-tier memory: session → daily → long-term → knowledge graph
- Deep Feishu/Lark integration: 112 TypeScript files covering nearly every API

**Install:**
```
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

Runs on macOS 12+ and Linux. Needs one API key (DeepSeek gives free credits on signup).

**Self-hosted benefits:**
- All data stays on your machine
- API keys stored locally only
- No telemetry (opt-in anonymous install counter only)
- MIT licensed

GitHub: https://github.com/xyva-yuangui/XyvaClaw
Website: https://www.xyvaclaw.com

Happy to answer any questions!
```

### r/LocalLLaMA 帖子内容

**标题**: Built a self-evolving AI assistant with lossless context, 38 skills, and 5-level model fallback — open source

**正文**:
```
Hey everyone,

Sharing a project I've been working on: xyvaClaw — an enhanced AI assistant platform built on OpenClaw.

The key technical decisions:

1. **Lossless Context Engine**: Instead of lossy compression, I built a custom engine (lossless-claw) that uses semantic segmentation + incremental summarization + entity tracking to preserve all critical information within the context window.

2. **Self-Evolution**: The assistant records its mistakes, tracks outcomes of decisions, and periodically reflects on behavior patterns. After ~1 month of use, there's a noticeable improvement in task completion quality.

3. **5-Level Fallback**: DeepSeek Chat → Qwen3.5+ → Kimi K2.5 → DeepSeek Reasoner → Qwen3 Max. Automatic switching, zero downtime.

4. **4-Tier Memory**: Session memory → Daily memory → Long-term memory → Knowledge graph. Prevents information loss across conversations.

Currently supports DeepSeek and Bailian (Qwen/Kimi/GLM/MiniMax) APIs. Works with any OpenAI-compatible endpoint too (Ollama, vLLM, etc.).

One-click install:
```
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

GitHub: https://github.com/xyva-yuangui/XyvaClaw
MIT licensed.

Would love feedback on the architecture!
```

---

## 二、Hacker News (Show HN)

### 发帖规则
- 标题格式必须是 **"Show HN: 项目名 — 一句话描述"**
- 不能太营销，要突出技术
- 链接直接放 GitHub 地址（HN 用户喜欢看代码）

### 标题
```
Show HN: xyvaClaw – Self-evolving AI assistant with 38 skills and lossless context
```

### 链接
```
https://github.com/xyva-yuangui/XyvaClaw
```

### 第一条评论（发布后立即在帖子下面回复）
```
Hi HN, I'm the author.

I built xyvaClaw over the past 6 months to solve my own frustrations with AI assistant tooling. It's built on the OpenClaw runtime with deep enhancements.

The three things I'm most proud of technically:

1. **Lossless context engine** — Most assistants use lossy compression for long conversations. I built a custom engine that preserves all critical information through semantic segmentation + incremental summarization + entity tracking.

2. **Self-evolution** — The system records errors, tracks decision outcomes, and does periodic self-reflection. It genuinely gets better with use — after ~4 weeks, I measured a significant reduction in error rate on recurring task types.

3. **5-level model fallback** — DeepSeek → Qwen → Kimi → DeepSeek Reasoner → Qwen Max. I haven't had a single downtime incident in 6 months despite individual API outages.

Other features: 38 pre-installed skills (browser automation, doc generation, video creation, stock screening), 4-tier memory system, deep Feishu/Lark integration (112 TS files).

Stack: Node.js (OpenClaw runtime), TypeScript (extensions), Python (some skills). Runs on macOS and Linux.

MIT licensed. Happy to discuss the architecture or answer any questions.
```

### 发帖步骤
1. 访问 https://news.ycombinator.com/
2. 注册/登录（需要先有 HN 账号，建议提前几天注册并正常互动）
3. 点击顶部 **"submit"**
4. Title 填: `Show HN: xyvaClaw – Self-evolving AI assistant with 38 skills and lossless context`
5. URL 填: `https://github.com/xyva-yuangui/XyvaClaw`
6. 提交后立即在自己帖子下面回复上面的评论
7. **最佳发帖时间**: 太平洋时间周二/周三上午 8-10 点（北京时间周二/周三晚上 11 点-凌晨 1 点）

### 注意事项
- HN 严禁刷票（不要让朋友投票，会被检测到并惩罚）
- 内容要真实、技术性强
- 回复每一个评论，态度友善
- 如果被问到和 AutoGPT、Dify 等的区别，诚实回答
