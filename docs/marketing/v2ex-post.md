# V2EX 发布帖

> 发布节点：推荐 /go/share 或 /go/programmer 或 /go/create
> 标题见下方

---

## 标题

开源了一个自进化 AI 助手平台 xyvaClaw：38 个技能 / 五级容灾 / 飞书集成 / 一条命令部署

## 正文

做了半年多，终于觉得可以拿出来见人了。

**xyvaClaw** 是一个跑在你自己机器上的 AI 助手平台，基于 OpenClaw 运行时深度增强。

和市面上的 AI 工具最大的区别：**它会自我进化——犯过的错自动记录，下次不再重复；用得越久越懂你。**

### 核心卖点

- 🧠 **四层记忆**：会话 → 日记忆 → 长期记忆 → 知识图谱，不再每次从零开始
- 🔄 **自我进化**：错误学习 + 效果追踪 + 主动反思 + 主动行动
- ⚡ **38 个内置技能**：浏览器自动化、AI 视频制作、量化选股、小红书发布、RAG 知识库...
- 🛡️ **五级模型容灾**：DeepSeek → Qwen → Kimi → Reasoner → Qwen Max，永不掉线
- 💬 **飞书深度集成**：112 个 TS 文件覆盖几乎所有飞书 API
- 🔒 **完全本地**：数据在你自己机器上，不上传任何第三方
- 📦 **一条命令部署**：

```bash
DEEPSEEK_API_KEY=sk-你的密钥 \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'
```

### 技术栈

- 运行时：OpenClaw (Node.js)
- 模型：DeepSeek V3.2 / 百炼（Qwen/Kimi/GLM/MiniMax）
- 飞书扩展：TypeScript
- 技能：Bash / Python / Node.js 混合
- 前端配置向导：React + Vite
- 部署：Bash 安装脚本，支持 macOS + Linux

### 链接

- GitHub：https://github.com/xyva-yuangui/XyvaClaw
- 官网：https://www.xyva.fun
- 协议：MIT
- QQ 交流群：1087471835

欢迎 Star、试用、提 Issue。一个人的项目，希望能帮到有同样需求的人。
