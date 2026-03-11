# 网站分发教程

> 如何通过网站分发 xyvaClaw，以及如何建立一个炫酷的官网

---

## 分发方式选择

### 方案对比

| 方式 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **GitHub 直接 clone** | 最简单、版本管理自动化 | 需要 git，需要网络 | ⭐⭐⭐⭐⭐ |
| **GitHub Release tar.gz** | 不需要 git，下载即用 | 需要手动更新 | ⭐⭐⭐⭐ |
| **官网下载页** | 最专业，品牌感强 | 需要建站和维护 | ⭐⭐⭐⭐ |
| **npm 包** | 前端圈友好 | 不适合非 Node 用户 | ⭐⭐⭐ |

### 推荐策略

**GitHub 为主 + 官网为辅**

1. **主要分发**：用户从 GitHub clone 或下载 Release
2. **官网作用**：品牌展示 + 引导到 GitHub + 在线文档
3. **不需要额外打包**：`git clone` 后直接 `bash xyvaclaw-setup.sh` 即可

---

## 方案 A: GitHub 分发（主力）

详见 [GITHUB-DISTRIBUTION-TUTORIAL.md](./GITHUB-DISTRIBUTION-TUTORIAL.md)

用户安装流程：
```bash
# 方式1: git clone
git clone https://github.com/xyva-yuangui/XyvaClaw.git
cd xyvaclaw && bash xyvaclaw-setup.sh

# 方式2: 下载 Release
# 从 GitHub Releases 页面下载 tar.gz
tar -xzf xyvaclaw-v1.0.0.tar.gz
cd xyvaclaw && bash xyvaclaw-setup.sh
```

---

## 方案 B: 官网分发（品牌加持）

### 为什么需要官网？

1. **第一印象**：炫酷的官网让人觉得项目专业
2. **SEO**：Google/百度搜索能找到你
3. **文档中心**：比 GitHub 的 Markdown 更友好
4. **品牌建设**：独立域名 = 独立品牌

### 建站方案选择

| 方案 | 成本 | 难度 | 效果 |
|------|------|------|------|
| **GitHub Pages + 静态站** | 免费 | 低 | ⭐⭐⭐⭐ |
| **Vercel + Next.js** | 免费 | 中 | ⭐⭐⭐⭐⭐ |
| **Netlify + 静态站** | 免费 | 低 | ⭐⭐⭐⭐ |
| **自建 VPS** | 付费 | 高 | ⭐⭐⭐⭐⭐ |

**推荐：Vercel（免费、速度快、自动部署）或 GitHub Pages（零配置）**

### 官网内容规划

```
xyvaclaw.dev (或 xyvaclaw.github.io)
├── / (首页 - 产品展示)
│   ├── Hero: 大标题 + 一句话 + 安装命令 + CTA 按钮
│   ├── Features: 6 大核心能力卡片
│   ├── Comparison: 对比原生 OpenClaw 的表格
│   ├── Skills: 技能展示（可折叠分组）
│   ├── Testimonials: 用户评价（后续添加）
│   └── Footer: GitHub / 文档 / 社区链接
├── /docs (文档)
├── /blog (博客/更新日志)
└── /download (下载引导)
```

---

## 部署到 GitHub Pages

### Step 1: 创建官网项目

我已经在 `/Users/momo/Desktop/xyvaclaw/website/` 中创建了官网源码。

### Step 2: 构建

```bash
cd ~/Desktop/xyvaclaw/website
npm install
npm run build
```

### Step 3: 部署到 GitHub Pages

方式 A — 使用 gh-pages 分支：
```bash
npm install -D gh-pages
npx gh-pages -d dist
```

方式 B — 在仓库 Settings 中配置：
1. Settings → Pages
2. Source 选 "Deploy from a branch"
3. Branch 选 `gh-pages` / root
4. 保存后等几分钟

访问 `https://YOUR_USERNAME.github.io/xyvaclaw/`

---

## 部署到 Vercel（推荐）

### Step 1: 连接 GitHub

1. 访问 [vercel.com](https://vercel.com) → Sign up with GitHub
2. Import → 选择 xyvaclaw 仓库
3. Root Directory 设为 `website`
4. Framework Preset 选 "Vite"
5. Build Command: `npm run build`
6. Output Directory: `dist`
7. Deploy!

### Step 2: 绑定域名（可选）

1. 在 Vercel Dashboard → Settings → Domains
2. 添加你的域名（如 xyvaclaw.dev）
3. 在域名 DNS 中添加 CNAME 记录指向 `cname.vercel-dns.com`

---

## 自定义域名

### 获取域名

| 注册商 | 推荐域名 | 价格 |
|--------|----------|------|
| Namecheap | xyvaclaw.dev | ~$12/年 |
| Cloudflare | xyvaclaw.com | ~$10/年 |
| 阿里云 | xyvaclaw.cn | ~¥30/年 |

### 免费替代

- `YOUR_USERNAME.github.io/xyvaclaw` (GitHub Pages)
- `xyvaclaw.vercel.app` (Vercel)
- `xyvaclaw.netlify.app` (Netlify)

---

## 总结

1. **不需要额外打包** — `git clone` + `bash xyvaclaw-setup.sh` 就够了
2. **GitHub Release** — 提供 tar.gz 下载给不想装 git 的用户
3. **官网** — 品牌加持，引导到 GitHub，提升专业感
4. **推荐路径**: GitHub Pages 或 Vercel 免费部署

---

*下一页准备好了？让我们来看看官网长什么样 👇*
