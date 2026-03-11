# 🐾 xyvaClaw

> 你的私人 AI 助手平台 — 一键部署，开箱即用

xyvaClaw 是基于 OpenClaw 运行时的品牌化 AI 助手平台，内置 38+ 技能、飞书通道集成、上下文引擎，支持 DeepSeek / 百炼 / 自定义 OpenAI 兼容模型。

## ✨ 特性

- **🚀 一键安装** — 一条命令完成全部部署
- **🌐 Web 配置向导** — 图形界面配置 API Key、通道、技能
- **🧠 多模型支持** — DeepSeek、百炼（Qwen/Kimi/GLM/MiniMax）、自定义 Provider
- **💬 飞书集成** — 通过飞书机器人与 AI 助手对话
- **🛠 38+ 技能** — 浏览器自动化、量化选股、内容创作、文档处理等
- **🔒 安全** — API Key 本地存储，不上传任何服务器
- **📦 跨平台** — 支持 macOS 和 Linux

## 🚀 快速开始

### macOS

```bash
# 下载
git clone https://github.com/yourname/xyvaclaw.git
cd xyvaclaw

# 一键安装
bash xyvaclaw-setup.sh
```

### Linux (Ubuntu/Debian/CentOS)

```bash
git clone https://github.com/yourname/xyvaclaw.git
cd xyvaclaw
bash xyvaclaw-setup-linux.sh
```

安装脚本会自动：
1. ✅ 检测并安装缺失依赖（Node.js 22+、Python 3、ffmpeg）
2. ✅ 安装 OpenClaw 运行时
3. ✅ 启动 Web 配置向导（或手动编辑 .env）
4. ✅ 部署配置和技能
5. ✅ 注册系统服务（开机自启）

## 🔑 需要的 API Key

| 密钥 | 必填 | 获取地址 |
|------|------|----------|
| DeepSeek API Key | 推荐 | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| 百炼 API Key | 推荐 | [bailian.console.aliyun.com](https://bailian.console.aliyun.com/) |
| 飞书 App ID/Secret | 选填 | [open.feishu.cn](https://open.feishu.cn/) |
| Tushare Token | 选填 | [tushare.pro](https://tushare.pro/) |

> 至少需要 DeepSeek 或 百炼 其中一个模型 Provider

## 📁 安装后目录结构

```
~/.xyvaclaw/
├── openclaw.json          # 主配置文件
├── workspace/
│   ├── SOUL.md            # AI 助手人格
│   ├── IDENTITY.md        # 助手身份
│   ├── AGENTS.md          # 操作规范
│   ├── skills/            # 38 个技能
│   └── memory/            # 记忆存储
├── extensions/
│   ├── feishu/            # 飞书通道
│   └── lossless-claw/     # 上下文引擎
├── logs/                  # 日志
└── secrets/               # 密钥文件
```

## 🛠 常用命令

```bash
# 启动
xyvaclaw gateway

# 查看状态
xyvaclaw gateway status

# 查看 agent
xyvaclaw agents list

# 查看定时任务
xyvaclaw cron list

# 健康检查
bash ~/.xyvaclaw/scripts/health-check.sh
```

## 📱 飞书配置

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用 → 添加机器人能力
3. 获取 App ID 和 App Secret
4. 配置事件订阅 → 回调 URL: `http://你的IP:18789/feishu/webhook`
5. 添加权限：消息读写、群组管理、文档读写等

## 🔧 手动配置（不使用向导）

```bash
# 复制 .env 模板
cp templates/.env.template ~/.xyvaclaw/.env

# 编辑填写 API Key
nano ~/.xyvaclaw/.env

# 生成配置
python3 installer/restore-config.py \
  config-base/openclaw.json.template \
  ~/.xyvaclaw/.env

# 移动到目标位置
mv openclaw.json ~/.xyvaclaw/
```

## 🛠 内置技能一览

### 核心
- **secret-manager** — 密钥管理
- **claw-shell** — Shell 执行
- **error-guard** — 错误防护
- **vision-reader** — 图片/OCR
- **browser-pilot** — 浏览器自动化
- **git** — Git 版本控制

### 内容创作
- **content-creator** — 多平台内容
- **auto-video-creator** — AI 视频
- **python-dataviz** — 数据可视化
- **excel-xlsx** / **word-docx** — 文档处理

### 数据
- **quant-strategy-engine** — 量化选股
- **auto-researcher** — 自动研究
- **knowledge-graph-memory** — 知识图谱
- **rag-knowledge-base** — 知识库 RAG

### 社交媒体
- **xhs-creator** / **xhs-publisher** — 小红书
- **reddit-readonly** — Reddit

### 自动化
- **system-control** — 系统控制
- **web-scraper** — 网页抓取
- **cron-scheduler** — 定时任务
- **workflow** / **batch** — 工作流

### 自我进化
- **self-improving-agent** — 从错误中学习
- **proactive-agent** — 主动行动
- **effect-tracker** — 效果追踪

## ❓ FAQ

**Q: 安装后多大？**
A: 约 15-20MB（不含 node_modules 和模型文件）

**Q: 首次启动慢？**
A: 首次启动会下载本地 embedding 模型（约 70MB），之后秒启。

**Q: 可以同时用多个模型吗？**
A: 可以。配置多个 Provider 后，系统会自动 fallback。

**Q: 密钥安全吗？**
A: 完全安全。所有密钥仅存储在本地 `~/.xyvaclaw` 目录中。

**Q: 如何更新？**
A: `npm update -g openclaw` 更新运行时，`git pull` 更新 xyvaClaw 配置。

## 📄 License

MIT
