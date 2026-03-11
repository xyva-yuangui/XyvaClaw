# GitHub 分发教程

> 从零开始把 xyvaClaw 推送到 GitHub 并吸引用户

---

## 前置准备

### 1. 注册 GitHub 账号
如果还没有 GitHub 账号：
1. 访问 [github.com](https://github.com)
2. 点击 Sign up → 填写用户名、邮箱、密码
3. 验证邮箱

### 2. 安装 Git（你的 Mac 已经有了）
```bash
# 验证
git --version
# 应该输出 git version 2.x.x
```

### 3. 配置 Git 身份
```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
```

### 4. 配置 GitHub 认证

推荐用 SSH Key（一次配置，永久使用）：

```bash
# 生成 SSH Key（如果没有）
ssh-keygen -t ed25519 -C "你的邮箱@example.com"
# 一路回车即可

# 复制公钥到剪贴板
pbcopy < ~/.ssh/id_ed25519.pub

# 如果 pbcopy 不可用
cat ~/.ssh/id_ed25519.pub
# 手动复制输出内容
```

然后在 GitHub 上添加 SSH Key：
1. 打开 [github.com/settings/keys](https://github.com/settings/keys)
2. 点击 "New SSH key"
3. Title 填 "My Mac"
4. Key type 选 "Authentication Key"
5. Key 粘贴刚才复制的公钥
6. 点击 "Add SSH key"

验证连接：
```bash
ssh -T git@github.com
# 应该输出: Hi username! You've successfully authenticated...
```

---

## Step 1: 在 GitHub 上创建仓库

1. 登录 GitHub → 右上角 `+` → **New repository**
2. 填写信息：
   - **Repository name**: `xyvaclaw`
   - **Description**: `🐾 xyvaClaw — Your Extended Virtual Agent. One-click AI assistant platform with 38+ skills, self-evolution, and deep Feishu integration.`
   - **Visibility**: 选择 **Public**（开源项目）
   - ⚠️ **不要**勾选 "Add a README file"（我们已经有了）
   - ⚠️ **不要**勾选 "Add .gitignore"（我们已经有了）
   - License: 选 MIT（我们已经有了，这里也可以不选）
3. 点击 **Create repository**

创建后 GitHub 会显示一个空仓库页面，上面有推送指令。

---

## Step 2: 推送代码到 GitHub

```bash
# 进入项目目录
cd ~/Desktop/xyvaclaw

# 添加 GitHub 远程仓库（用你自己的用户名替换 YOUR_USERNAME）
git remote add origin git@github.com:YOUR_USERNAME/xyvaclaw.git

# 推送到 GitHub
git push -u origin main
```

如果用 HTTPS 而非 SSH：
```bash
git remote add origin https://github.com/YOUR_USERNAME/xyvaclaw.git
git push -u origin main
# 会弹窗要求登录 GitHub
```

推送成功后，刷新 GitHub 仓库页面，你的代码就上去了！

---

## Step 3: 设置仓库信息（美化门面）

### 3.1 设置 Topics（标签）

在仓库页面 → 右侧 About 区域 → 点击齿轮图标 ⚙️

添加 Topics（这些标签帮助别人发现你的项目）：
```
ai-assistant, openclaw, chatbot, feishu, lark, deepseek, 
self-evolving-ai, automation, quantitative-trading, 
one-click-install, chinese-ai
```

### 3.2 设置 Description

```
🐾 xyvaClaw — One-click AI assistant with 38+ skills, self-evolution engine, 5-level model fallback, and deep Feishu/Lark integration. Powered by DeepSeek & Qwen.
```

### 3.3 设置 Website

如果后续创建了官网，填入官网 URL。

---

## Step 4: 创建首个 Release

Release 是 GitHub 的正式版本发布，用户可以在这里下载打包好的文件。

### 4.1 创建 Git Tag

```bash
cd ~/Desktop/xyvaclaw
git tag -a v1.0.0 -m "xyvaClaw v1.0.0 - Initial release"
git push origin v1.0.0
```

### 4.2 在 GitHub 上创建 Release

1. 仓库页面 → 右侧 "Releases" → **Create a new release**
2. 填写：
   - **Tag**: 选择 `v1.0.0`
   - **Release title**: `xyvaClaw v1.0.0 — 首个正式版`
   - **Description**（可以用下面的模板）：

```markdown
# 🐾 xyvaClaw v1.0.0

首个正式发布版本。

## ✨ 亮点

- 🚀 **一键安装** — macOS 和 Linux 一条命令完成部署
- 🌐 **Web 配置向导** — 浏览器中完成 API Key 和通道配置
- 🧠 **双模型引擎** — DeepSeek V3.2 + 百炼（Qwen/Kimi/GLM/MiniMax）
- 🔄 **自我进化** — 错误学习、效果追踪、主动反思
- 💬 **飞书深度集成** — 112 个 TS 源文件，覆盖几乎所有飞书 API
- 🛠 **38 个内置技能** — 浏览器自动化、量化选股、内容创作等
- 📊 **5 级 Fallback** — 模型故障自动切换，零宕机

## 📦 安装

\```bash
git clone https://github.com/YOUR_USERNAME/xyvaclaw.git
cd xyvaclaw
bash xyvaclaw-setup.sh    # macOS
bash xyvaclaw-setup-linux.sh  # Linux
\```

## 📋 需求

- Node.js 22+
- Python 3.10+
- 至少一个 AI 模型 API Key（DeepSeek 或百炼）
```

3. 可选：上传打包文件
```bash
# 先在本地打包
bash scripts/xyvaclaw-pack.sh
# 会在桌面生成 xyvaclaw-YYYYMMDD_HHMMSS.tar.gz
```
然后把 tar.gz 拖到 Release 页面的 "Attach binaries" 区域。

4. 点击 **Publish release**

---

## Step 5: 推广策略

### 5.1 在 GitHub 上推广

- **Star 自己的项目**（示范效应）
- **写好 README**（最重要！下面已经帮你准备了中英文版本）
- **添加 Shield 徽章**（显示版本、License、Stars 等）
- **提交到 GitHub Trending**：打好 Topics 标签后自然会被索引

### 5.2 社区推广

| 平台 | 策略 |
|------|------|
| **V2EX** | 发到 /t/share 板块，标题突出"一键部署"和"自我进化" |
| **掘金** | 写技术文章介绍架构设计 |
| **知乎** | 回答 AI 助手相关问题，顺带提及 |
| **Twitter/X** | 发英文推文 @AI_dev 社区 |
| **Reddit** | r/selfhosted, r/artificial, r/ChatGPT |
| **Hacker News** | Show HN 帖子，突出技术亮点 |
| **Product Hunt** | 作为新产品发布 |
| **微信公众号** | 写中文教程 |

### 5.3 README 是最好的广告

GitHub 用户决定是否 Star 一个项目，90% 取决于 README 的前 3 屏。下面是为你准备的中英文 README。

---

## Step 6: 日常维护

### 更新代码
```bash
cd ~/Desktop/xyvaclaw
# 做了修改后
git add -A
git commit -m "描述你的改动"
git push
```

### 发布新版本
```bash
git tag -a v1.1.0 -m "v1.1.0 - 新功能描述"
git push origin v1.1.0
# 然后在 GitHub 上创建对应的 Release
```

### 查看 Star 和 Fork
- 仓库页面右上角可以看到 Stars 和 Forks 数量
- Settings → Insights 可以看详细的流量数据

---

## 常见问题

### Q: 推送时报错 "Permission denied"
→ SSH Key 没配置好，重新执行 Step 0 的 SSH Key 配置

### Q: 推送时报错 "remote already exists"
```bash
git remote remove origin
git remote add origin git@github.com:YOUR_USERNAME/xyvaclaw.git
```

### Q: 如何删除已推送的 commit
```bash
# ⚠️ 慎用，会覆盖历史
git reset --hard HEAD~1
git push --force
```

### Q: 如何让别人参与贡献
在仓库中创建 `CONTRIBUTING.md` 文件，说明贡献规范和 PR 流程。

---

*恭喜！你的项目已经在 GitHub 上了。接下来把 README 写好，就等着收 Star 了！*
