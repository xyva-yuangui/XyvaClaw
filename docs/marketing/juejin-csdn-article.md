# 我做了个会「自我进化」的 AI 助手，38 个技能一键部署，开源了

> 适用平台：掘金、CSDN
> 发布建议：掘金选择标签「人工智能」「开源」「效率工具」；CSDN 选择分类「人工智能」

---

## 前言

大家好，我是圆规。

过去半年我一直在用 [OpenClaw](https://openclaw.ai/)（一个开源 AI 助手运行时）搭建自己的 AI 工作流。用着用着，我发现几个痛点：

- **配置太复杂** — 需要手动编辑 JSON，得理解 schema 才能跑起来
- **模型挂了就完蛋** — 没有容灾，DeepSeek 一抽风我就没助手用了
- **上下文经常丢** — 对话一长，AI 就开始"忘事"
- **技能要一个个装** — 每个都要自己配，费时间

于是我在 OpenClaw 的基础上做了深度增强，做成了 **xyvaClaw** — 一个开箱即用、会自我进化的 AI 助手平台。现在开源了，分享给大家。

## xyvaClaw 是什么？

一句话概括：**OpenClaw 的增强版，面向实际使用场景深度优化。**

| 对比项 | 原版 OpenClaw | xyvaClaw |
|--------|-------------|----------|
| 安装 | 手动编辑 JSON | **一键安装 + 图形化向导** |
| 模型 | 自己配 | 预配置 DeepSeek V3.2 + 百炼（Qwen/Kimi/GLM） |
| 容灾 | 无 | **五级自动切换，零宕机** |
| 上下文 | 有损压缩 | **无损上下文引擎** |
| 技能 | 一个个装 | **38 个技能预装** |
| 记忆 | 基础 | **四层记忆：会话→日→长期→知识图谱** |
| 进化 | 无 | **错误学习 + 效果追踪 + 自我反思** |
| 飞书 | 基础收发 | **112 个 TS 文件，覆盖几乎所有飞书 API** |

## 核心亮点

### 1. 真正的"一键安装"

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

运行后自动：
- 检测并安装所有依赖（Node.js、Python、ffmpeg）
- 弹出浏览器配置向导（填 API Key 就行）
- 部署 38 个技能 + 所有配置
- 配置开机自启动

不会用 git 的同学也可以直接[下载 ZIP](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip)。

### 2. 自我进化引擎（这是我最得意的部分）

xyvaClaw 不只是一个工具，它会**越用越聪明**：

- **错误学习**：犯过的错自动记录，下次直接规避
- **效果追踪**：每个决策都追踪结果，形成正反馈循环
- **主动行动**：不等你问，主动发现任务并执行
- **自我反思**：周期性分析行为模式，持续优化策略

举个例子：第一周它可能会在某些任务上犯错，但第二周同样的场景它就能规避了。用一个月后，你会明显感觉到它比刚装好时聪明很多。

### 3. 五级模型容灾

不怕任何一个模型 API 挂掉：

```
DeepSeek Chat → Qwen3.5+ → Kimi K2.5 → DeepSeek Reasoner → Qwen3 Max
```

自动切换，用户无感知。再也不用担心半夜 DeepSeek 抽风了。

### 4. 38 个内置技能

| 类别 | 技能示例 |
|------|---------|
| 核心 | Shell 执行、浏览器自动化、图片识别、Git |
| 内容创作 | AI 视频制作、Word/Excel/PPT 生成、数据可视化 |
| 飞书增强 | 高级文档操作、智能消息管理 |
| 数据分析 | A 股量化选股、自动调研、知识图谱 |
| 自动化 | 定时任务、工作流、批量处理 |
| 社交媒体 | 小红书内容创作/发布、Reddit 抓取 |

### 5. 深度飞书集成

112 个 TypeScript 源文件，覆盖：消息、文档、多维表格、日历、审批、云盘、Wiki。

可以在飞书群里直接指挥 AI 助手干活 — 写文档、查数据、发审批、管理日程。

## 技术架构

```
~/.xyvaclaw/
├── openclaw.json          # 主配置
├── workspace/
│   ├── SOUL.md            # AI 人设定义
│   ├── skills/            # 38 个技能模块
│   └── memory/            # 持久化记忆
├── extensions/
│   ├── feishu/            # 飞书集成（112 TS 文件）
│   └── lossless-claw/     # 无损上下文引擎
└── logs/                  # 运行日志
```

## 快速体验

### 准备
- 一个 API Key：[DeepSeek](https://platform.deepseek.com/api_keys)（推荐，注册送免费额度）或 [百炼](https://bailian.console.aliyun.com/)

### 安装
```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

### 启动
```bash
xyvaclaw gateway
# 浏览器打开 http://localhost:18789
```

## 最后

项目完全开源，MIT 协议，个人和商用都可以。

- **GitHub**: https://github.com/xyva-yuangui/XyvaClaw
- **官网**: https://www.xyvaclaw.com
- **QQ 群**: 1087471835
- **Discord**: https://discord.gg/QABg4Z2Mzu

如果觉得有用，求个 ⭐ Star，这是持续更新的最大动力！

有问题欢迎在评论区交流，或者加群讨论。
