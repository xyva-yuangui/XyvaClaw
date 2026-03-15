# xyvaClaw 五大决策方案 — 等待决策后执行

> 生成时间：2026-03-15  
> 请阅读后告诉我你的选择，我会立即执行修改。

---

## 问题 1：为什么没有 GitHub Release 版本？

### 原因
我们之前只做了 `git push` 把代码推到 main 分支，但 **从未创建过 GitHub Release（发行版）**。Release 是 GitHub 上独立于代码提交的"版本发布"功能，需要手动创建或通过 CI/API 创建。

### 没有 Release 的影响
- 用户无法看到版本号和更新日志
- 无法下载特定版本的打包文件（zip/tar.gz）
- GitHub 仓库看起来"不专业"，没有版本历史
- SEO/GEO 受影响（AI 模型会参考 Release 信息）
- `downloadUrl` 在 JSON-LD 中指向 releases 页面但实际是空的

### 建议：立即创建 v1.0.0 Release

**方案 A（推荐）：我通过 GitHub API 帮你创建**
- 我直接用 API 创建 v1.0.0 tag + Release
- 自动附带源码 zip/tar.gz 下载
- 你只需要说"执行"

**方案 B：你手动创建**
- 打开 https://github.com/xyva-yuangui/XyvaClaw/releases/new
- Tag: `v1.0.0`，Target: `main`
- Title: `v1.0.0 — 首个正式版`
- 写 Release Notes

> **👉 你的决策：选 A 还是 B？**

---

## 问题 2：后续更新怎么操作？

### 推荐流程（语义化版本 + Release）

```
版本号规则：
  v1.0.0 → v1.0.1   修复 bug（patch）
  v1.0.0 → v1.1.0   新增功能（minor）
  v1.0.0 → v2.0.0   重大变更/不兼容（major）
```

### 每次更新的标准操作

```bash
# 1. 修改代码
# 2. 更新版本号（在 setup 脚本、package.json、网站 JSON-LD 等处）
# 3. 提交
git add -A && git commit -m "feat: 新功能描述"

# 4. 打 tag
git tag -a v1.1.0 -m "v1.1.0: 新增 xxx 功能"

# 5. 推送代码 + tag
git push origin main --tags

# 6. 创建 Release（通过 GitHub 网页 或 API）
```

### 自动化选项

**方案 A（推荐）：我帮你写一个 release 脚本**
- `bash scripts/release.sh 1.1.0` 一条命令完成：更新版本号 → 提交 → tag → push → 创建 Release
- 最省事

**方案 B：手动操作**
- 每次按上面的步骤手动执行

**方案 C：GitHub Actions CI/CD**
- 推送 tag 时自动创建 Release
- 需要配置 GitHub Actions（我可以帮你写）

> **👉 你的决策：选 A、B 还是 C？（我推荐 A + C 结合）**

---

## 问题 3：安装时检测已有 OpenClaw / 其他厂商 Claw 的处理方案

### 当前状况

当前安装脚本（Step 2）只检查 `openclaw` 命令是否存在：
- 存在 → 跳过安装，直接复用
- 不存在 → 执行 `npm install -g openclaw@latest`

**问题**：没有检测已有的 OpenClaw 配置目录（`~/.openclaw`）、其他 Claw 产品、以及可能的端口冲突。

### 需要检测的情况

| 场景 | 检测方法 | 风险 |
|------|---------|------|
| 已安装原生 OpenClaw，有 `~/.openclaw/` | 检查目录是否存在 | 端口冲突（都用 18789）、配置互相覆盖 |
| 已安装 QClaw（腾讯） | 检查 `/Applications/QClaw.app` 或进程 | 端口冲突、不同 OpenClaw 版本 |
| 已安装 AutoClaw（智谱） | 检查 `/Applications/AutoClaw.app` 或进程 | 同上 |
| 已安装 WorkBuddy（腾讯） | 检查 `/Applications/WorkBuddy.app` 或进程 | 同上 |
| 已安装 ArkClaw（火山引擎） | 云端服务，不冲突 | 无冲突 |
| 已安装 miclaw（小米） | 小米设备独占，不冲突 | 无冲突 |
| 已安装 MaxClaw / KimiClaw / DuClaw | 云端服务，不冲突 | 无冲突 |
| CoPaw | 检查进程或安装目录 | 可能端口冲突 |

### 核心原则
1. **绝不自动删除用户数据** — 只能在用户明确确认后操作
2. **优先共存** — 如果不冲突就不动
3. **安全备份** — 任何操作前先备份
4. **安装失败安全** — 检测逻辑本身不能导致安装中断

### 推荐方案：分级处理

```
检测流程：
  ┌─ 检测 openclaw 命令是否存在
  │   ├── 存在 → 检查版本是否兼容
  │   │   ├── 兼容 → 直接复用 ✅
  │   │   └── 不兼容 → 询问是否升级
  │   └── 不存在 → 正常安装
  │
  ├─ 检测 ~/.openclaw/ 目录是否存在
  │   ├── 存在 → ⚠️ 已有 OpenClaw 配置
  │   │   ├── 询问用户：
  │   │   │   1) 保留现有配置，xyvaClaw 使用独立目录 ~/.xyvaclaw（默认，最安全）
  │   │   │   2) 备份现有配置到 ~/.openclaw.backup.日期，然后继续
  │   │   │   3) 卸载现有 OpenClaw 配置（按官方方式）
  │   │   │   4) 退出安装
  │   │   └── 无论选什么，都不会丢数据
  │   └── 不存在 → 继续
  │
  ├─ 检测本地 Claw 应用（QClaw / AutoClaw / WorkBuddy / CoPaw）
  │   ├── 存在 → ⚠️ 提示可能端口冲突
  │   │   ├── 建议：关闭该应用后再安装，或修改 xyvaClaw 端口
  │   │   └── 不自动卸载这些应用（它们是独立产品）
  │   └── 不存在 → 继续
  │
  ├─ 检测端口 18789 是否被占用
  │   ├── 被占用 → 提示哪个进程在用，建议先关闭或换端口
  │   └── 空闲 → 继续
  │
  └─ 检测 OpenClaw launchd/systemd 服务
      ├── 存在 → 提示可能冲突
      │   └── 询问是否停止并禁用原有服务
      └── 不存在 → 继续
```

### OpenClaw 官方卸载方法（已查阅官方文档）

```bash
# 方法一：CLI 还在的情况
openclaw gateway stop           # 停止服务
openclaw gateway uninstall      # 卸载自启动服务
rm -rf "${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"  # 删除数据目录
npm rm -g openclaw              # 卸载 CLI

# 方法二：macOS 手动清理（CLI 不在了）
launchctl bootout gui/$UID/ai.openclaw.gateway
rm -f ~/Library/LaunchAgents/ai.openclaw.gateway.plist
rm -rf ~/.openclaw
# 如果有 profile:
# launchctl bootout gui/$UID/ai.openclaw.<profile>
# rm -rf ~/.openclaw-<profile>

# 方法三：macOS App 版
rm -rf /Applications/OpenClaw.app
```

### 其他厂商 Claw 产品卸载方法

| 产品 | 卸载方式 |
|------|---------|
| QClaw（腾讯） | 拖拽 `/Applications/QClaw.app` 到废纸篓，或用腾讯电脑管家卸载 |
| AutoClaw（智谱） | 拖拽 `/Applications/AutoClaw.app` 到废纸篓 |
| WorkBuddy（腾讯） | 拖拽 `/Applications/WorkBuddy.app` 到废纸篓 |
| CoPaw | 拖拽 App 到废纸篓，清理 `~/.copaw/` |
| ArkClaw（火山引擎） | 云端服务，无需本地卸载 |
| MaxClaw / KimiClaw / DuClaw | 云端/订阅服务，取消订阅即可 |
| miclaw（小米） | 小米设备系统级，无法卸载 |

### 关于"能不能直接帮用户卸载"

**强烈建议：不要自动卸载其他厂商产品。**

理由：
1. 法律风险 — 自动删除其他公司的软件可能引发纠纷
2. 用户信任 — 用户会觉得 xyvaClaw 在搞"流氓软件"行为
3. 数据安全 — 用户可能在那些产品里有重要数据
4. 不必要 — xyvaClaw 用独立目录 `~/.xyvaclaw`，与其他 Claw 天然隔离

**正确做法：检测 → 提示 → 让用户自己决定 → 提供卸载命令参考**

> **👉 你的决策：**
> - **A（推荐）**：检测已有 Claw + 端口冲突，提示用户但不自动卸载，提供手动卸载命令参考
> - **B**：检测已有 Claw，询问用户是否帮忙卸载 OpenClaw（仅 OpenClaw，不动其他厂商）
> - **C**：不检测，保持现状（有冲突风险）

---

## 问题 4：GitHub 上更新能不能不留记录？

### 结论：可以，但有代价

| 方法 | 原理 | 效果 | 风险 |
|------|------|------|------|
| `git push --force` | 强制覆盖远程历史 | commit 历史完全替换 | ⚠️ 已 fork/clone 的用户会冲突 |
| Squash Merge | 多个 commit 压成一个 | 减少历史条目 | ⚠️ 丢失细粒度历史 |
| `git rebase -i` + `--force` | 交互式编辑历史后强推 | 精确控制显示什么 | ⚠️ 同上 |
| Orphan Branch | 创建无历史的新分支 | 彻底干净的历史 | ⚠️ 所有人需要重新 clone |
| `--amend` + `--force` | 修改最后一个 commit | 最近的改动不留痕迹 | ⚠️ 只影响最后一个 commit |

### 实际操作方式

#### 方式一：Squash + Force（推荐用于"特殊功能更新"）

```bash
# 假设你在 dev 分支开发了特殊功能
git checkout dev
# ... 做了多次 commit ...

# 合并到 main 时 squash 成一个 commit
git checkout main
git merge --squash dev
git commit -m "feat: 常规功能优化"  # 用模糊的 commit message

# 或者直接 amend + force push
git push --force origin main
```

#### 方式二：用单独的私有仓库开发，再 cherry-pick 到公开仓库

```
私有仓库（详细 commit 历史）→ cherry-pick 或 squash → 公开仓库（干净历史）
```

这是最安全的方案：
- 私有仓库保留完整开发记录
- 公开仓库只显示你想让别人看到的内容
- 两个仓库完全独立

### 注意事项
- GitHub 即使 force push，**旧的 commit 仍然可以通过 SHA 直接访问约 90 天**（除非联系 GitHub 支持清理）
- 如果有人 fork 了你的仓库，旧 commit 会留在他们的 fork 里
- **不要在 commit message 或代码注释中写敏感信息**，这是最根本的安全措施

> **👉 你的决策：**
> - **A（推荐）**：创建一个私有开发仓库，特殊功能在私有仓库开发，squash 后推到公开仓库
> - **B**：直接在公开仓库用 `--amend` + `--force` 覆盖最近的 commit
> - **C**：使用 orphan branch 偶尔"重置"整个历史
> - **D**：不处理，commit 历史无所谓

---

## 问题 5：xyvaClaw 性能和功能升级方案

### 当前能力评估

**已有的 38 个 Skills：**

| 类别 | Skills | 状态 |
|------|--------|------|
| 核心 | secret-manager, claw-shell, error-guard, vision-reader, browser-pilot | ✅ 完善 |
| 自我进化 | self-improving-agent, effect-tracker, proactive-agent | ✅ 完善 |
| 文档 | word-docx, excel-xlsx, content-creator | ✅ 完善 |
| 飞书 | feishu-doc-extended + 112 TS files | ✅ 完善 |
| 数据 | quant-strategy-engine, python-dataviz, chart-image | ✅ 完善 |
| 视频 | auto-video-creator, video-subtitles | ✅ 完善 |
| 自动化 | cron-scheduler, cron-mastery, workflow, batch | ✅ 完善 |
| 社交 | xhs-creator, xhs-publisher, reddit-readonly | ✅ 基础 |
| 研究 | auto-researcher, web-scraper, rag-knowledge-base | ✅ 基础 |
| 其他 | git, code-review, test-runner, screenshot-sender, smart-messenger, system-control, miniflux-news, commerce-travel-shopper, knowledge-graph-memory, qwen-image, agent-team-orchestration | ✅ 各有功能 |

**已有的扩展：**
- feishu（112 TS 文件）— 飞书深度集成
- lossless-claw — 无损上下文引擎

### 升级方案（分优先级）

#### 🔴 P0 — 立即可做（1-2 天）

| 升级项 | 说明 | 影响 |
|--------|------|------|
| **健康检查 Skill** | 定时检查 gateway 状态、API 连通性、内存/磁盘使用、日志异常 | 运维零担忧 |
| **自动更新检查** | 启动时检查 GitHub 是否有新版本，提示用户更新 | 用户粘性 |
| **安装后首次引导** | 第一次启动时提供交互式教程（"试试让我帮你生成一个 Excel"） | 小白友好 |
| **日志轮转优化** | 自动清理超过 7 天的日志，防止磁盘满 | 稳定性 |

#### 🟡 P1 — 短期可做（1-2 周）

| 升级项 | 说明 | 影响 |
|--------|------|------|
| **PPT 生成 Skill** | 用 python-pptx 生成 PowerPoint，目前只有 Word 和 Excel | 补齐办公三件套 |
| **邮件 Skill** | 收发邮件（IMAP/SMTP），自动整理、回复、归类 | 高频需求 |
| **日历/提醒 Skill** | 本地提醒系统（macOS Calendar/Notification 集成） | 个人助手核心 |
| **PDF 处理 Skill** | 读取、提取、合并、转换 PDF | 高频需求 |
| **语音输入/输出** | 集成 Whisper 语音识别 + edge-tts 语音合成，支持语音对话 | 差异化体验 |
| **微信集成** | 类似 QClaw 的微信消息接入（需谨慎，有封号风险） | 用户量最大的渠道 |
| **Telegram 集成** | Telegram Bot 接入 | 海外用户渠道 |

#### 🟢 P2 — 中期规划（1-2 月）

| 升级项 | 说明 | 影响 |
|--------|------|------|
| **MCP 协议支持** | 支持 Model Context Protocol，对接更多第三方工具 | 生态兼容 |
| **本地模型支持** | Ollama / vLLM 集成，支持完全离线运行 | 隐私场景 |
| **多 Agent 协作增强** | agent-team-orchestration 升级，支持并行任务、任务依赖图 | 复杂任务处理 |
| **插件市场** | xyvaClaw Skill Store，用户可发布和安装社区技能 | 生态建设 |
| **Web Dashboard** | 一个漂亮的 Web 管理界面（任务列表、日志查看、技能管理、配置修改） | 小白友好 |
| **移动端适配** | 通过 PWA 或小程序在手机上与 xyvaClaw 交互 | 移动场景 |
| **知识库增强** | RAG 升级：支持上传文档建立私有知识库，支持向量检索 | 企业级 |

#### 🔵 P3 — 长期愿景（成为"万能的神"）

| 升级项 | 说明 | 影响 |
|--------|------|------|
| **Multi-modal 增强** | 图片理解+生成、视频理解、音频处理的统一接口 | 全模态 |
| **电脑控制（Computer Use）** | 直接操作 macOS GUI（类似 Anthropic Computer Use），自动完成任何桌面操作 | 革命性 |
| **IoT 集成** | 智能家居控制（米家、HomeKit） | 生活助手 |
| **分布式部署** | 多台机器组成集群，任务自动分发 | 企业级 |
| **行业垂直包** | 金融分析包、程序员包、自媒体运营包、电商包 | 精准用户群 |
| **AI 训练/微调** | 基于用户数据微调本地小模型，个性化能力更强 | 终极进化 |

### 成为"万能的神"的路径

```
当前状态：
  ✅ 能思考（多模型推理）
  ✅ 能记忆（四层记忆系统）
  ✅ 能进化（自我进化引擎）
  ✅ 能看（vision-reader）
  ✅ 能写（文档生成）
  ✅ 能上网（browser-pilot）
  ✅ 能编程（claw-shell + code-review）
  ✅ 能办公（飞书集成）

缺少的关键能力（优先补齐）：
  ❌ 能听 → 语音输入（Whisper）
  ❌ 能说 → 语音输出（edge-tts 已装，需集成到对话流）
  ❌ 能发邮件 → 邮件 Skill
  ❌ 能做 PPT → PPT Skill
  ❌ 能读 PDF → PDF Skill
  ❌ 能提醒 → 日历/提醒 Skill
  ❌ 能控制电脑 → Computer Use
  ❌ 能离线运行 → 本地模型
  ❌ 能在手机用 → 移动端

补齐以上能力后，xyvaClaw 就真正是一个「万能的神」了。
```

> **👉 你的决策：**
> - 选择你想优先实现的升级项，我来写代码
> - 或者告诉我一个方向（比如"先把 P0 全做了"），我按优先级执行
> - 如果有特定的功能需求，也可以直接告诉我

---

## 总结：需要你做的 5 个决策

| # | 问题 | 推荐选项 | 你的选择 |
|---|------|---------|---------|
| 1 | Release 创建方式 | A（我通过 API 创建） | ? |
| 2 | 后续更新流程 | A+C（release 脚本 + GitHub Actions） | ? |
| 3 | 已有 Claw 处理方式 | A（检测+提示，不自动卸载） | ? |
| 4 | 不留记录的更新方式 | A（私有仓库开发 + squash 推送） | ? |
| 5 | 功能升级优先级 | P0 全做 + P1 选择性做 | ? |

请告诉我你的选择，我立即执行！
