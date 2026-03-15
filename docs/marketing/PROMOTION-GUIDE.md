# xyvaClaw 推广操作指南

> 按顺序执行以下步骤。每个步骤都有详细操作说明。
> 所有文章内容已准备好，在 `docs/marketing/` 目录下。

---

## 第一步：安全 — 重新生成 GitHub Token（⚠️ 紧急）

你的 PAT token 已在聊天中暴露，必须立即更换。

1. 打开 https://github.com/settings/tokens
2. 找到你当前使用的 token，点击 **Delete**
3. 点击 **Generate new token (classic)**
4. 勾选 `repo` 权限
5. 生成后**保存到安全的地方**（比如 macOS 钥匙串或 1Password）
6. 配置 Git 自动记住密码：
   ```bash
   git config --global credential.helper osxkeychain
   ```
7. 下次 `git push` 时输入：
   - Username: `xyva-yuangui`
   - Password: 你的新 token

---

## 第二步：GitHub 仓库优化（5 分钟）

### 2.1 设置仓库描述和主题标签

1. 打开 https://github.com/xyva-yuangui/XyvaClaw
2. 点击右侧齿轮图标 ⚙️（About 区域）
3. **Description** 填入：
   ```
   🐾 One-click AI assistant platform with 38+ skills, self-evolution engine, 5-level model fallback, deep Feishu integration. 一键部署的自进化 AI 助手平台。
   ```
4. **Website** 填入：`https://www.xyva.fun`
5. **Topics** 填入以下标签（逐个输入后回车）：
   ```
   ai-assistant
   ai-agent
   chatbot
   feishu
   lark
   deepseek
   self-evolution
   automation
   open-source
   one-click-deploy
   openclaw
   skills
   chinese
   ```
6. 勾选 **Releases**、**Packages** 复选框
7. 点击 **Save changes**

### 2.2 创建第一个 Release

1. 先在终端打包：
   ```bash
   cd ~/Desktop/xyvaclaw
   bash scripts/xyvaclaw-pack.sh
   ```
   这会在桌面生成 `xyvaclaw-日期.tar.gz`

2. 打开 https://github.com/xyva-yuangui/XyvaClaw/releases/new
3. **Tag**: 输入 `v1.0.0`，选择 "Create new tag on publish"
4. **Release title**: `xyvaClaw v1.0.0 — First Public Release`
5. **Description** 填入：
   ```markdown
   ## 🐾 xyvaClaw v1.0.0

   首个公开发布版本。

   ### 核心特性
   - ✅ 38+ 内置技能（浏览器自动化、视频制作、量化选股、小红书发布等）
   - ✅ 自我进化引擎（错误学习 + 效果追踪 + 主动反思）
   - ✅ 五级模型容灾（DeepSeek → Qwen → Kimi → Reasoner → Qwen Max）
   - ✅ 无损上下文引擎（Lossless-Claw）
   - ✅ 飞书深度集成（112 个 TypeScript 源文件）
   - ✅ 一条命令无人值守部署（`--auto` 模式）
   - ✅ Web 配置向导

   ### 安装

   ```bash
   # 一行命令安装（macOS / Linux）
   DEEPSEEK_API_KEY=sk-你的密钥 \
     bash -c 'git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh --auto'
   ```

   ### 环境要求
   - macOS 12+ 或 Linux (Ubuntu 22+, Debian 12+, CentOS 8+)
   - Node.js 22+（安装器自动安装）
   - Python 3.10+（安装器自动安装）
   - 至少一个 API Key：[DeepSeek](https://platform.deepseek.com/api_keys) 或 [百炼](https://bailian.console.aliyun.com/)

   ---
   官网：https://www.xyva.fun
   交流群：QQ 1087471835
   ```
6. 拖拽上传桌面上的 `.tar.gz` 文件
7. 点击 **Publish release**

### 2.3 设置 Social Preview 图片

1. 用 Canva (https://canva.com) 创建图片：
   - 尺寸：**1280 × 640 像素**
   - 深色背景（#0f172a）
   - 左侧放 🐾 xyvaClaw 品牌名（大字）
   - 右侧列出 3 个卖点：
     - 38+ Skills | Self-Evolution | Feishu Integration
   - 底部放 `www.xyva.fun` 和 `MIT License`
2. 打开 https://github.com/xyva-yuangui/XyvaClaw/settings
3. 下拉到 **Social preview**
4. 点击 **Edit** → 上传图片
5. 保存

---

## 第三步：提交搜索引擎（10 分钟）

### 3.1 Google Search Console

1. 打开 https://search.google.com/search-console
2. 点击左侧 **添加资源**
3. 选择 **URL 前缀**，输入 `https://www.xyva.fun`
4. 验证方式选 **HTML 标签**，将 meta 标签添加到 `website/index.html` 的 `<head>` 中
5. 验证成功后，左侧菜单 → **Sitemap** → 输入 `sitemap.xml` → 提交
6. 左侧菜单 → **URL 检查** → 输入 `https://www.xyva.fun` → 请求编入索引

### 3.2 百度站长平台

1. 打开 https://ziyuan.baidu.com
2. 注册/登录后，点击 **用户中心 → 站点管理 → 添加网站**
3. 输入 `www.xyva.fun`
4. 验证方式选 **HTML 标签验证**
5. 将百度给的 `<meta name="baidu-site-verification" content="xxx">` 添加到 `website/index.html`
6. 验证成功后 → **普通收录 → sitemap** → 提交 `https://www.xyva.fun/sitemap.xml`
7. 手动提交首页 URL：`https://www.xyva.fun`

### 3.3 Bing Webmaster

1. 打开 https://www.bing.com/webmasters
2. 可以用 Google Search Console 账号直接导入
3. 或手动添加 `www.xyva.fun`
4. 提交 sitemap

---

## 第四步：发布推广文章（按优先级）

### 4.1 知乎（最高优先级，中文流量最大）

1. 打开 https://zhuanlan.zhihu.com/write
2. 复制 `docs/marketing/zhihu-article.md` 的内容
3. 粘贴后调整格式（知乎编辑器支持 Markdown）
4. 添加话题标签：`开源项目`、`AI助手`、`人工智能`、`效率工具`、`飞书`
5. 封面图：用 Canva 做一张（建议和 GitHub Social Preview 同款）
6. 发布

**发布后的推广动作：**
- 去以下知乎问题下回答，引用你的文章：
  - 搜索"有什么好用的 AI 助手"
  - 搜索"飞书机器人推荐"
  - 搜索"开源 AI 项目推荐"
  - 搜索"DeepSeek 能做什么"

### 4.2 掘金

1. 打开 https://juejin.cn/editor/drafts/new
2. 复制 `docs/marketing/juejin-csdn-article.md` 的内容
3. 标签选择：`开源`、`AI`、`前端`、`Node.js`
4. 分类选择：`开源` 或 `人工智能`
5. 发布

### 4.3 CSDN

1. 打开 https://editor.csdn.net/md
2. 复制同一篇 `juejin-csdn-article.md`
3. 标签：`AI`、`开源`、`DeepSeek`、`飞书`、`智能体`
4. 发布

### 4.4 V2EX

1. 打开 https://www.v2ex.com/new
2. 节点选择：`分享创造` 或 `程序员`
3. 复制 `docs/marketing/v2ex-post.md` 的内容
4. **注意**：V2EX 不支持 Markdown 表格，需要简化格式
5. 发布

### 4.5 Product Hunt（英文流量）

1. 打开 https://www.producthunt.com/posts/new
2. 按 `docs/marketing/producthunt-submission.md` 的内容填写
3. **最佳发布时间**：美国太平洋时间周二凌晨 0:01（北京时间周二下午 4:01）
4. 发布后立即发第一条评论（First Comment 已准备好）
5. 分享到你的社交媒体

### 4.6 提交 Awesome Lists PR

1. 按 `docs/marketing/awesome-lists-pr.md` 的指引
2. Fork 对应仓库 → 编辑 → 提交 PR
3. PR 标题和描述已准备好

---

## 第五步：制作 OG Image（社交分享图）

当别人在微信/Twitter/Facebook 分享你的网站链接时显示的图片。

1. 打开 https://canva.com
2. 创建 **1200 × 630** 尺寸的图片
3. 设计建议：
   - 背景色：深蓝渐变（#0f172a → #1e293b）
   - 中间大字：🐾 xyvaClaw
   - 副标题：Your AI That Evolves | 你的 AI 会进化
   - 底部三个标签：38+ Skills · Self-Evolution · Feishu Integration
   - 右下角：www.xyva.fun
4. 导出为 PNG，命名为 `og-image.png`
5. 放到 `website/public/og-image.png`
6. 我会帮你在 index.html 中添加引用

---

## 第六步：持续运营

### 每周做
- [ ] 在知乎回答 1-2 个 AI 相关问题，自然引用 xyvaClaw
- [ ] 更新 GitHub Release（有新功能时）
- [ ] 在 QQ 群中分享使用技巧

### 每月做
- [ ] 掘金/CSDN 发一篇技术文章（分享某个技能的实现细节）
- [ ] 更新 sitemap.xml 的日期
- [ ] 检查搜索引擎收录情况

### 里程碑目标
- [ ] GitHub 100 ⭐ → 可以申请 GitHub Trending
- [ ] GitHub 500 ⭐ → 申请加入 GitHub Collections
- [ ] 知乎文章 1000 赞 → 可以开启知乎好物推荐

---

## 文件清单

所有推广素材都在 `docs/marketing/` 目录下：

| 文件 | 用途 |
|------|------|
| `zhihu-article.md` | 知乎专栏文章 |
| `juejin-csdn-article.md` | 掘金/CSDN 技术文章 |
| `v2ex-post.md` | V2EX 发帖 |
| `producthunt-submission.md` | Product Hunt 提交 |
| `awesome-lists-pr.md` | Awesome 列表 PR |
| `PROMOTION-GUIDE.md` | 本指南 |
