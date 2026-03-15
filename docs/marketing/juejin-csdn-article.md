# 开源了一个自进化 AI 助手平台：38 个技能 + 五级容灾 + 飞书深度集成 | xyvaClaw

> 发布平台：掘金 / CSDN
> 建议标签：开源、AI、智能体、飞书、DeepSeek、自动化、效率工具

---

## 前言

做了半年多的 AI 助手项目，从一开始给自己用的脚本，到现在 38 个技能、112 个飞书 API 文件、五级模型容灾的完整平台，终于开源了。

**GitHub**：[github.com/xyva-yuangui/XyvaClaw](https://github.com/xyva-yuangui/XyvaClaw)
**官网**：[www.xyva.fun](https://www.xyva.fun)

这篇文章会讲清楚：
1. xyvaClaw 是什么、解决什么问题
2. 技术架构和核心设计思路
3. 怎么一条命令部署
4. 几个有意思的技术细节

---

## 一、项目概述

xyvaClaw 是基于 [OpenClaw](https://github.com/nicepkg/openclaw) 运行时的**增强型 AI 助手平台**。

你可以理解为：**OpenClaw + 预调好的模型 + 38 个实战技能 + 自我进化引擎 + 企业级飞书集成 = xyvaClaw**。

### 核心特性

| 特性 | 说明 |
|------|------|
| **一键部署** | `bash xyvaclaw-setup.sh --auto` 全自动安装，支持无人值守 |
| **38+ 技能** | 浏览器自动化、文档处理、视频制作、量化选股、小红书发布等 |
| **五级模型容灾** | DeepSeek V3.2 → Qwen3.5+ → Kimi K2.5 → DeepSeek Reasoner → Qwen3 Max |
| **无损上下文** | Lossless-Claw 引擎，长对话不丢信息 |
| **四层记忆** | 会话 → 日记忆 → 长期记忆 → 知识图谱 |
| **自我进化** | 错误学习 + 效果追踪 + 主动反思 + 主动行动 |
| **飞书集成** | 112 个 TypeScript 文件，覆盖消息/文档/表格/审批/日历/云盘 |
| **本地部署** | 数据完全私有，不依赖任何 SaaS 平台 |

---

## 二、技术架构

### 目录结构

```
~/.xyvaclaw/
├── openclaw.json          # 主配置（模型、容灾、并发等）
├── workspace/
│   ├── SOUL.md            # AI 人格定义
│   ├── AGENTS.md          # 操作协议
│   ├── TOOLS.md           # 工具知识速查
│   ├── skills/            # 38 个技能模块
│   │   ├── browser-pilot/
│   │   ├── auto-video-creator/
│   │   ├── quant-strategy-engine/
│   │   └── ...
│   └── memory/            # 持久化记忆
│       ├── 2026-03-15.md  # 日记忆
│       └── working-buffer.md
├── extensions/
│   ├── feishu/            # 飞书集成（112 TS 文件）
│   └── lossless-claw/     # 无损上下文引擎
├── agents/                # 多 Agent 配置
├── config/                # 别名、运行时参数
└── logs/                  # 运行日志
```

### 模型容灾设计

这是我觉得最实用的设计之一。单一模型不可靠——DeepSeek 偶尔 503、百炼偶尔限流。五级容灾的配置方式：

```json
{
  "models": {
    "chat": {
      "provider": "deepseek",
      "model": "deepseek-chat",
      "fallbacks": [
        { "provider": "bailian", "model": "qwen-plus" },
        { "provider": "bailian", "model": "kimi-k2" },
        { "provider": "deepseek", "model": "deepseek-reasoner" },
        { "provider": "bailian", "model": "qwen-max" }
      ]
    }
  }
}
```

模型挂了自动切，对用户完全透明。

### 自我进化系统

四个组件协同工作：

1. **Error Guard**：捕获所有错误，写入 `.learnings/ERRORS.md`，下次遇到同类问题直接规避
2. **Effect Tracker**：记录每个决策的结果——成功率、用户反馈、耗时，形成正反馈循环
3. **Proactive Agent**：心跳机制驱动，每次心跳扫描 `docs/todo.md`、日志、异常，主动发现并处理任务
4. **Self-Reflection**：周期性分析行为模式，识别可改进的地方

核心思路：**AI 不应该是静态的工具，它应该像一个新入职的员工——每天都比昨天更懂你的业务。**

### 无损上下文引擎

OpenClaw 原生的上下文压缩是有损的——长对话会丢信息。Lossless-Claw 扩展解决这个问题：

- 对话超过阈值时，不是简单截断，而是提取关键信息写入 `working-buffer.md`
- 被压缩的内容仍然可以按需召回
- 实测 10 万 token 对话无信息丢失

---

## 三、安装部署

### 一行命令（无人值守）

```bash
# macOS
DEEPSEEK_API_KEY=sk-你的密钥 \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'

# Linux
DEEPSEEK_API_KEY=sk-你的密钥 \
  bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup-linux.sh --auto'
```

`--auto` 做了什么：
- 检测并自动安装缺失依赖（Node.js 22+、Python 3、ffmpeg）
- 安装 OpenClaw 运行时
- 从环境变量注入 API Key
- 部署 38 个技能 + 飞书/无损引擎扩展
- 生成身份文件（SOUL.md / AGENTS.md / MEMORY.md）
- 注册系统服务（macOS LaunchAgent / Linux systemd）
- 后台启动 Gateway

也支持环境变量传入飞书配置：

```bash
DEEPSEEK_API_KEY=sk-xxx \
FEISHU_APP_ID=cli_xxx \
FEISHU_APP_SECRET=xxx \
bash xyvaclaw-setup.sh --auto
```

### 交互式安装（Web 向导）

去掉 `--auto` 会启动 Web 配置向导，浏览器中可视化填写 API Key。

---

## 四、几个有意思的技术细节

### 1. 安装脚本的 `auto_confirm` 模式

为了实现真正的无人值守安装，我封装了 `auto_confirm()` 函数替代所有 `read -p`：

```bash
auto_confirm() {
    local prompt="$1" default="${2:-y}"
    if [ "$AUTO_MODE" = true ]; then
        REPLY="$default"
        echo -e "$prompt $default (auto)"
        return 0
    fi
    read -p "$prompt" -n 1 -r
    echo ""
}
```

每个交互点都有合理的默认值，`--auto` 时自动应答，交互式时正常提示。

### 2. Wizard 前端构建的双场景处理

安装脚本需要处理两种场景：
- **Git clone**：`setup-wizard/dist/` 不存在（gitignored），需要 `npm install` + `vite build`
- **分发包**：`dist/` 已打包进去，只需 `npm install --production`

```bash
NEED_BUILD=false
if [ ! -f "$WIZARD_DIR/dist/index.html" ]; then
    NEED_BUILD=true
fi

if [ "$NEED_BUILD" = true ]; then
    (cd "$WIZARD_DIR" && npm install && npx vite build)
else
    (cd "$WIZARD_DIR" && npm install --production)
fi
```

### 3. macOS `sed -i` 的坑

macOS 的 `sed -i` 和 Linux 不一样——macOS 要求 `sed -i ''`，或者用 `sed -i.bak` 再删除备份。安装脚本里用了后者：

```bash
sed -i.bak "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "$ENV_FILE"
rm -f "${ENV_FILE}.bak"
```

---

## 五、后续计划

- [ ] Windows WSL 支持
- [ ] Docker 一键部署
- [ ] Web UI 管理面板
- [ ] 更多 AI 模型适配（Claude、Gemini）
- [ ] 插件市场

---

## 开源信息

- **GitHub**：[github.com/xyva-yuangui/XyvaClaw](https://github.com/xyva-yuangui/XyvaClaw)
- **官网**：[www.xyva.fun](https://www.xyva.fun)
- **协议**：MIT
- **交流群**：QQ群 1087471835
- **作者**：圆规（Xyva-yuangui）

欢迎 Star ⭐、Fork、提 Issue。这是一个人的项目，但希望它能帮到更多人。
