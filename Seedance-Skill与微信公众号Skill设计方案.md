# Seedance Video Skill + 微信公众号自动排版发文 Skill — 设计方案

> 基于实际调研和测试的完整设计方案，供决策后开发。
> 日期: 2026-03-16

---

## 一、Seedance Video Skill（即梦 AI 视频生成）

### 1.1 需求回顾

| 项目 | 要求 |
|------|------|
| 模型 | Seedance 2.0（即梦 AI） |
| 视频时长 | 15s |
| 视频比例 | 9:16（竖屏短视频） |
| 首尾帧 | 支持首帧/尾帧上传 |
| 痛点 | 即梦 AI 无官方 API，只有网页版 |

### 1.2 调研发现 — 三条可行路径

#### 方案 A：jimeng-free-api-all（⭐ 推荐）

**项目**: [github.com/wwwzhouhui/jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all)

**原理**: 逆向即梦内部 API，封装为 OpenAI 兼容接口。Seedance 2.0 请求通过 Playwright headless 浏览器代理注入 `a_bogus` 签名绕过反爬。

**核心能力**:
- ✅ Seedance 2.0 / 2.0-fast 视频生成
- ✅ 多模态素材上传（图片/视频/音频混合）
- ✅ 首帧控制（通过图片上传 + `@1` 占位符）
- ✅ 9:16 竖屏比例
- ✅ 4-15 秒时长
- ✅ OpenAI 兼容 API 格式
- ✅ 多账号轮询
- ✅ Docker 一键部署
- ✅ 版本活跃（最新 v0.8.6，2026-02-20），已解决 shark 反爬

**调用方式**:
```bash
# Seedance 2.0 + 首帧图片
curl -X POST http://localhost:8000/v1/videos/generations \
  -H "Authorization: Bearer <sessionid>" \
  -F "model=jimeng-video-seedance-2.0" \
  -F "prompt=@1 图片中的人物缓缓转身，阳光洒在脸上" \
  -F "ratio=9:16" \
  -F "duration=15" \
  -F "files=@/path/to/first_frame.jpg"

# Seedance 2.0-fast（更快但质量略低）
curl -X POST http://localhost:8000/v1/videos/generations \
  -H "Authorization: Bearer <sessionid>" \
  -F "model=jimeng-video-seedance-2.0-fast" \
  -F "prompt=一只橘猫在窗台上打哈欠" \
  -F "ratio=9:16" \
  -F "duration=10"
```

**认证方式**: 从即梦网站 Cookie 获取 `sessionid`，支持多账号逗号分隔轮询。

**部署**: Docker 一条命令
```bash
docker run -it -d --init --name jimeng-api \
  -p 8000:8000 \
  -e TZ=Asia/Shanghai \
  wwwzhouhui569/jimeng-free-api-all:latest
```

**优势**:
- 不需要操作浏览器 UI，直接 API 调用
- 已解决即梦所有反爬机制（shark/a_bogus）
- OpenAI 格式兼容，可复用 sora-video 的工作流设计
- 社区活跃，持续更新

**风险**:
- 🟡 逆向工程项目，字节可能封堵（但项目持续应对）
- 🟡 sessionid 会过期，需要定期更新
- 🟡 依赖即梦每日赠送的 66 积分（约 66 次生成），超出需购买

#### 方案 B：browser2api（Playwright 全自动化）

**项目**: [github.com/Rabornkraken/browser2api](https://github.com/Rabornkraken/browser2api)

**原理**: 用 Playwright + Chrome CDP 完全自动化即梦网页，模拟人工操作。

**优势**:
- 模拟真实用户行为，不走内部 API
- 适用面更广（也支持 Google Flow 等）

**风险**:
- 🔴 UI 变动即失效，维护成本高
- 🔴 操作速度慢（需等待页面渲染）
- 🔴 并发能力差
- 🟡 反检测风险更高

#### 方案 C：火山引擎官方 API

即梦 AI 于 2025-09-02 携手火山引擎全面开放 API，包括视频生成 3.0pro、Seedance 等模型。

**优势**:
- ✅ 官方渠道，稳定可靠
- ✅ 企业级 SLA

**风险**:
- 🔴 需要企业认证 + 付费
- 🔴 接入流程较长
- 🟡 API 价格未知（企业级定价）

### 1.3 方案对比

| 维度 | 方案 A (jimeng-free-api) | 方案 B (browser2api) | 方案 C (火山引擎) |
|------|:---:|:---:|:---:|
| **开发成本** | ⭐⭐⭐⭐⭐ 极低 | ⭐⭐ 高 | ⭐⭐⭐ 中 |
| **稳定性** | ⭐⭐⭐ 中 | ⭐⭐ 低 | ⭐⭐⭐⭐⭐ 高 |
| **功能完整度** | ⭐⭐⭐⭐⭐ 全面 | ⭐⭐⭐ 基本 | ⭐⭐⭐⭐⭐ 全面 |
| **维护成本** | ⭐⭐⭐⭐ 低 | ⭐ 极高 | ⭐⭐⭐⭐⭐ 几乎无 |
| **费用** | 免费(66次/天) | 免费 | 付费(未知) |
| **Seedance 2.0** | ✅ | ✅ | ✅ |
| **首帧上传** | ✅ | ✅ | ✅ |
| **9:16 竖屏** | ✅ | ✅ | ✅ |
| **15s 时长** | ✅ | ✅ | ✅ |
| **并发能力** | 中(多账号) | 低 | 高 |

### 1.4 推荐方案：A（jimeng-free-api-all）

**理由**:
1. 开发成本最低 — Docker 部署 + API 调用，我们只需写 Skill 封装层
2. 功能完整 — 支持所有需求（Seedance 2.0、首帧、9:16、15s）
3. 与现有 sora-video 架构一致 — 可复用工作流（提示词优化→生成→下载→飞书）
4. 费用可控 — 每日 66 次免费，日均 50-100 条需要 2 个账号即可覆盖

### 1.5 Seedance Skill 架构设计

```
用户剧本/创意 + 首帧图片（可选）
       ↓
  DeepSeek 提示词优化（复用 sora-video 的 prompt_optimizer）
       ↓
  jimeng-free-api-all (Docker, :8000)
  ├── model: jimeng-video-seedance-2.0
  ├── ratio: 9:16
  ├── duration: 15
  └── files: [首帧图片]
       ↓
  轮询等待完成 → 下载视频
       ↓
  本地保存 (output/video/YYYY-MM-DD/HHMMSS_seedance_摘要.mp4)
       ↓
  飞书推送（视频链接 + 本地路径）
```

**Skill 文件结构**:
```
skills/seedance-video/
├── SKILL.md
├── config/
│   └── default.json          # API 配置（端口、sessionid、默认参数）
└── scripts/
    ├── check.py              # 健康检查
    ├── seedance_api.py       # API 封装（调用 jimeng-free-api-all）
    ├── seedance_video.py     # 主入口（workflow/create/check）
    └── prompt_optimizer.py   # → 软链接到 sora-video 的 prompt_optimizer.py
```

### 1.6 部署步骤

```bash
# 1. 部署 jimeng-free-api-all
docker pull wwwzhouhui569/jimeng-free-api-all:latest
docker run -it -d --init --name jimeng-api \
  -p 8000:8000 \
  -e TZ=Asia/Shanghai \
  wwwzhouhui569/jimeng-free-api-all:latest

# 2. 获取 sessionid
# 打开 https://jimeng.jianying.com/ → 登录 → F12 → Application → Cookies → sessionid

# 3. 配置 OpenClaw
# 在 seedance-video/config/default.json 中填入 sessionid

# 4. 测试
python3 scripts/seedance_video.py check
python3 scripts/seedance_video.py workflow --prompt "一只猫在窗台上打哈欠"
```

### 1.7 已知风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| sessionid 过期 | 高 | 中 | 多账号轮询 + 过期告警 → 飞书通知 |
| 字节封堵内部 API | 中 | 高 | 跟进社区更新；备选方案 B 或 C |
| 每日积分不足 | 中 | 中 | 多账号(2-3个) × 66 = 132-198 次/天 |
| 反爬升级 | 低 | 高 | jimeng-free-api-all 社区持续应对 |

---

## 二、微信公众号自动排版发文 Skill

### 2.1 需求回顾

| 项目 | 要求 |
|------|------|
| 排版 | AI 自动排版，输出美观的公众号文章 |
| 发文 | 自动创建草稿 + 发布 |
| 管理 | 链接和管理微信公众号 |

### 2.2 调研发现 — 微信公众号 API 全景

微信官方提供了完整的公众号开发者 API，支持全流程自动化：

**核心 API 链路**:
```
获取 access_token
    ↓
上传文章图片 → 获取 image URL
    ↓
上传封面图 → 获取 thumb_media_id
    ↓
新建草稿 (draft/add) → 获取 media_id
    ├── title: 文章标题
    ├── content: HTML 正文（支持富文本排版）
    ├── thumb_media_id: 封面图
    ├── author: 作者
    ├── digest: 摘要
    └── content_source_url: 原文链接
    ↓
发布草稿 (freepublish/submit) → publish_id
    ↓
查询发布状态 (freepublish/get)
    ↓
获取已发布文章列表 (freepublish/batchget)
```

### 2.3 前置条件

| 条件 | 是否必须 | 说明 |
|------|:---:|------|
| **已认证的公众号** | ✅ 必须 | 微信 2025 年起仅认证账号支持「发布」操作，未认证/测试号只能存草稿 |
| **认证费用** | — | 个人/企业均可，300 元/年 |
| **服务器配置** | ✅ 必须 | 微信需要验证你的服务器地址（callback URL） |
| **AppID + AppSecret** | ✅ 必须 | 在公众号后台获取 |
| **IP 白名单** | ✅ 必须 | 在公众号后台设置服务器 IP |

### 2.4 核心功能设计

#### 2.4.1 AI 排版引擎

用户输入原始 Markdown 或纯文本 → DeepSeek 自动排版为公众号 HTML。

**排版模板系统**:
```
用户输入文章内容（Markdown/纯文本）
       ↓
  DeepSeek 排版优化
  ├── 根据内容类型自动选择排版模板
  │   ├── tech_article: 技术文章（代码块+目录）
  │   ├── story_article: 叙事文章（引用+场景描写）
  │   ├── list_article: 清单型（表格+数字标题）
  │   └── analysis_article: 分析报告（图表+数据卡片）
  ├── 自动处理:
  │   ├── 标题层级 → 微信兼容的 section 样式
  │   ├── 代码块 → 带背景色的 pre 标签
  │   ├── 图片 → 居中 + 圆角 + 阴影
  │   ├── 引用 → 左侧色条 + 浅色背景
  │   ├── 列表 → 自定义图标 + 间距
  │   ├── 分隔线 → 装饰性分隔
  │   └── 强调 → 品牌色高亮
  └── 输出微信兼容的内联样式 HTML
       ↓
  用户预览确认（飞书推送 HTML 预览 / 本地 HTML 文件）
       ↓
  确认后:
  ├── 上传文章图片 (uploadimg API)
  ├── 上传封面图 (addmaterial API)
  ├── 创建草稿 (draft/add API)
  └── 发布 (freepublish/submit API)
```

#### 2.4.2 公众号管理

| 功能 | API | 说明 |
|------|-----|------|
| 文章发布 | `draft/add` + `freepublish/submit` | 创建草稿 → 发布 |
| 文章管理 | `draft/batchget` + `freepublish/batchget` | 查看草稿箱 + 已发布文章 |
| 素材管理 | `material/addmaterial` + `material/batchgetmaterial` | 图片/音频/视频素材 |
| 粉丝管理 | `user/get` + `user/info` | 粉丝列表 + 用户信息 |
| 菜单管理 | `menu/create` + `menu/get` | 自定义菜单 |
| 评论管理 | `comment/open` + `comment/list` | 开启/管理评论 |
| 数据统计 | `datacube/*` | 用户/图文/接口分析 |

### 2.5 Skill 架构设计

**文件结构**:
```
skills/wechat-publisher/
├── SKILL.md
├── config/
│   ├── default.json           # 公众号配置（AppID、AppSecret、模板选择）
│   ├── templates/             # 排版模板
│   │   ├── tech.html          # 技术文章模板
│   │   ├── story.html         # 叙事文章模板
│   │   ├── list.html          # 清单型模板
│   │   └── analysis.html      # 分析报告模板
│   └── styles/
│       └── base.css           # 基础微信兼容样式（内联化）
└── scripts/
    ├── check.py               # 健康检查（access_token 有效性）
    ├── wechat_api.py          # 微信 API 封装
    ├── formatter.py           # AI 排版引擎（Markdown → 微信 HTML）
    ├── wechat_publisher.py    # 主入口（format/preview/publish/manage）
    └── template_engine.py     # 排版模板引擎
```

**主入口命令**:
```bash
# 健康检查
python3 scripts/wechat_publisher.py check

# AI 排版预览
python3 scripts/wechat_publisher.py format --input article.md --template auto --preview

# 创建草稿
python3 scripts/wechat_publisher.py draft --input article.md --title "标题" --cover cover.jpg

# 发布
python3 scripts/wechat_publisher.py publish --media-id MEDIA_ID

# 完整工作流（排版→预览→确认→发布）
python3 scripts/wechat_publisher.py workflow --input article.md --title "标题" --cover cover.jpg

# 管理
python3 scripts/wechat_publisher.py list-drafts
python3 scripts/wechat_publisher.py list-published
python3 scripts/wechat_publisher.py stats
```

### 2.6 排版示例

**输入** (Markdown):
```markdown
# AI 漫剧行业分析

## 市场规模
AI漫剧市场规模达200亿，同比增长45%。

## 用户画像
- 用户总量1.2亿
- 18-35岁为主
- 女性占比62%

> 行业专家认为，AI漫剧将在3年内成为内容消费主流形态。
```

**输出** (微信兼容 HTML — 自动内联样式):
```html
<section style="padding:20px;background:#fff;">
  <h1 style="font-size:22px;font-weight:bold;color:#1a1a1a;
    border-bottom:3px solid #07C160;padding-bottom:8px;margin-bottom:20px;">
    AI 漫剧行业分析
  </h1>

  <h2 style="font-size:18px;color:#333;margin:24px 0 12px;
    padding-left:12px;border-left:4px solid #07C160;">
    市场规模
  </h2>
  <p style="font-size:15px;color:#3f3f3f;line-height:1.8;margin:8px 0;">
    AI漫剧市场规模达<strong style="color:#07C160;">200亿</strong>，
    同比增长<strong style="color:#07C160;">45%</strong>。
  </p>

  <h2 style="...">用户画像</h2>
  <ul style="padding-left:0;list-style:none;">
    <li style="padding:6px 0;font-size:15px;line-height:1.6;">
      <span style="color:#07C160;margin-right:8px;">●</span>用户总量1.2亿
    </li>
    ...
  </ul>

  <blockquote style="border-left:4px solid #07C160;background:#f6f8fa;
    padding:12px 16px;margin:16px 0;border-radius:4px;font-size:14px;
    color:#666;">
    行业专家认为，AI漫剧将在3年内成为内容消费主流形态。
  </blockquote>
</section>
```

### 2.7 技术要点

1. **微信 HTML 限制**:
   - 不支持外部 CSS/JS
   - 所有样式必须内联（inline style）
   - 不支持 `class`、`id`
   - 图片必须用微信域名（上传后获取微信 URL）
   - 不支持 `iframe`、`video` 等标签
   - 链接仅支持公众号文章链接和微信白名单域名

2. **access_token 管理**:
   - 有效期 2 小时，需定期刷新
   - 每日获取上限 2000 次
   - 建议缓存 + 过期前 5 分钟刷新

3. **图片处理**:
   - 文章内图片需先通过 `uploadimg` 上传到微信服务器
   - 封面图通过 `addmaterial` 上传为永久素材
   - 返回的微信 URL 替换文章中的原始图片链接

### 2.8 前置确认事项

在开发前，需要你确认以下信息：

| # | 确认项 | 说明 |
|---|--------|------|
| 1 | **公众号类型** | 订阅号 or 服务号？ |
| 2 | **是否已认证** | 未认证只能存草稿，不能发布 |
| 3 | **AppID 和 AppSecret** | 在公众号后台 → 开发 → 基本配置 获取 |
| 4 | **服务器 IP** | 用于设置 IP 白名单 |
| 5 | **callback URL** | 微信验证服务器地址（可用 ngrok 临时） |
| 6 | **排版风格偏好** | 品牌色？字体偏好？排版模板？ |
| 7 | **发文频率** | 每日/每周几篇？是否需要定时发布？ |

---

## 三、结论与建议

### 3.1 Seedance Video Skill

| 项目 | 结论 |
|------|------|
| **可行性** | ✅ 高。jimeng-free-api-all 项目成熟，API 兼容 OpenAI 格式 |
| **推荐方案** | 方案 A：jimeng-free-api-all (Docker 部署) |
| **开发周期** | 1-2 天（复用 sora-video 架构） |
| **费用** | 免费（66 次/天/账号，多账号可扩展） |
| **风险** | 中。逆向工程项目，需跟进社区更新 |
| **前置工作** | 1) Docker 部署 jimeng-free-api-all<br>2) 获取即梦 sessionid |

**建议**: ✅ **立即开发**。成本低、收益明显、与现有 sora-video 架构高度复用。

### 3.2 微信公众号 Skill

#### ⚠️ 个人号（未认证）限制

微信自 2025 年起规定：**仅认证账号支持「发布」操作**。未认证个人号只能：
- ✅ 调用 API 创建草稿（draft/add）
- ✅ 上传素材（图片/封面）
- ❌ 不能通过 API 自动发布（freepublish/submit 会报权限错误）

#### 个人号可行方案

| 方案 | 说明 | 可行性 |
|------|------|:------:|
| **A. API草稿 + 手动发布** | AI排版→API创建草稿→飞书通知→手动登录mp.weixin.qq.com点发布 | ✅ 已实现 |
| **B. 认证升级** | 花300元/年认证 → 解锁API自动发布 | ✅ 一劳永逸 |
| **C. Playwright自动化** | 用browser-pilot操控mp.weixin.qq.com后台自动点发布 | 🟡 可行但脆弱 |

**当前实现**: 采用方案A（API草稿+手动发布），代码已支持认证号自动发布的切换。

| 项目 | 结论 |
|------|------|
| **可行性** | ✅ 高。个人号可用API创建草稿+排版，手动发布一键完成 |
| **推荐方案** | API草稿 + 手动发布 + 6种AI排版风格 |
| **开发状态** | ✅ 已完成（6种风格、AI排版、规则排版、草稿创建、预览） |
| **费用** | 0元（个人号）/ 300元/年（认证后可全自动） |
| **风险** | 低。官方API，仅发布需手动 |

### 3.3 开发状态（已完成）

```
✅ Seedance Video Skill — skills/seedance-video/
   ├── API封装（jimeng-free-api-all兼容）
   ├── 完整工作流（提示词优化→生成→下载→本地保存→飞书通知）
   ├── 首帧/尾帧上传支持
   ├── 快速/标准双模型
   └── 健康检查

✅ WeChat Publisher Skill — skills/wechat-publisher/
   ├── 6种内置排版风格（business/tech/story/minimalist/magazine/academic）
   ├── AI智能排版（DeepSeek驱动）+ 规则引擎排版
   ├── 自动风格检测
   ├── 微信HTML清洗（防抹除）
   ├── 图片自动上传（防盗链突破）
   ├── 草稿箱管理
   ├── 手机模拟预览（375px）
   ├── 个人号/认证号双模式支持
   └── 健康检查
```

### 3.4 待你操作

**Seedance**:
1. 部署Docker: `docker run -d --name jimeng-api -p 8000:8000 wwwzhouhui569/jimeng-free-api-all:latest`
2. 获取即梦sessionid: 登录 https://jimeng.jianying.com → F12 → Cookie → sessionid
3. 设置环境变量: `export JIMENG_SESSION_ID=你的sessionid`
4. 测试: `python3 skills/seedance-video/scripts/check.py`

**微信公众号**:
1. 登录 mp.weixin.qq.com → 设置与开发 → 基本配置
2. 获取 AppID 和 AppSecret
3. 在IP白名单中添加你的服务器IP
4. 设置环境变量: `export WECHAT_APP_ID=xxx WECHAT_APP_SECRET=xxx`
5. 测试: `python3 skills/wechat-publisher/scripts/check.py`
6. （可选）认证公众号 → 300元/年 → 解锁自动发布

---

*本方案基于 2026-03-16 实际调研数据。核心参考：*
- *jimeng-free-api-all v0.8.6 (2026-02-20)*
- *微信公众号开发者文档 (developers.weixin.qq.com)*
- *browser2api (Playwright 方案，备选)*
- *火山引擎即梦 API (企业方案，备选)*
