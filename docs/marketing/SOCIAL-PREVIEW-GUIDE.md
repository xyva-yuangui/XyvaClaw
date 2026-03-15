# GitHub Social Preview 图 — 是什么 & 怎么设置

---

## 什么是 Social Preview 图？

当有人在**微信、QQ、Twitter、Discord、Slack、飞书**等平台分享你的 GitHub 仓库链接时，会自动展示一张预览卡片。

比如分享 `https://github.com/xyva-yuangui/XyvaClaw` 到微信群，消息会变成：

```
┌──────────────────────────────────┐
│  [你设置的 Social Preview 图片]    │
│                                  │
│  xyva-yuangui/XyvaClaw           │
│  Your Extended Virtual Agent     │
│  — 你的超级 AI 助手               │
│  github.com                      │
└──────────────────────────────────┘
```

**如果不设置**，GitHub 会自动生成一个灰色的默认卡片，非常丑，而且没有吸引力。

**设置了之后**，可以展示一张精心设计的宣传图，大大提升点击率。

---

## 图片要求

| 项目 | 要求 |
|------|------|
| **尺寸** | **1280 × 640 像素**（宽 × 高，2:1 比例） |
| **格式** | PNG 或 JPG |
| **文件大小** | < 1MB |
| **内容建议** | 项目名 + 一句话介绍 + Logo + 核心卖点 |

---

## 设计建议

### 内容应该包含

1. **项目名**: xyvaClaw
2. **一句话描述**: "自我进化的 AI 助手平台" 或 "Self-evolving AI Assistant"
3. **Logo**: 你的 logo.png
4. **3-5 个核心卖点图标/文字**:
   - 🔄 自我进化
   - ⚡ 38+ 技能
   - 🛡️ 五级容灾
   - 🧠 无损上下文
   - 💬 飞书集成

### 风格建议

- **背景色**: 深色渐变（和你官网风格一致）
- **文字颜色**: 白色为主，品牌色点缀
- **字体**: 简洁的无衬线体
- **布局**: 左边 Logo + 项目名，右边核心卖点列表

### 参考示例

看看这些热门开源项目的 Social Preview：
- https://github.com/vercel/next.js （简洁 Logo + 项目名）
- https://github.com/langchain-ai/langchain （Logo + 描述 + 核心概念）
- https://github.com/oven-sh/bun （大 Logo + 极简文字）

---

## 制作工具（免费）

### 方案 1: Canva（最简单，推荐）

1. 访问 https://www.canva.com/ （免费注册）
2. 点击 **"创建设计"** → **"自定义尺寸"** → 输入 **1280 × 640**
3. 选择一个深色模板
4. 添加你的 Logo（上传 logo.png）
5. 添加文字：项目名 + 描述 + 核心卖点
6. 下载为 PNG

### 方案 2: Figma（更灵活）

1. 访问 https://www.figma.com/ （免费注册）
2. 新建画布 1280 × 640
3. 自由设计
4. 导出为 PNG

### 方案 3: 让 AI 生成

1. 打开任何 AI 图片生成工具（如 DALL-E、Midjourney）
2. 提示词: "A professional GitHub social preview image for an open source project called xyvaClaw, dark gradient background, modern tech style, with text 'xyvaClaw - Self-evolving AI Assistant', include icons for skills, evolution, and reliability, 1280x640 pixels"
3. 生成后下载

---

## 如何上传到 GitHub

### 详细步骤（带截图说明）

1. 打开浏览器，访问你的仓库: https://github.com/xyva-yuangui/XyvaClaw

2. 点击仓库页面的 **"Settings"**（设置）标签
   - 位置：仓库页面最右边的标签栏，在 "Insights" 旁边
   - ⚠️ 不是你个人账号的 Settings，是**仓库的** Settings

3. 向下滚动到 **"Social preview"** 区域
   - 大约在页面中间偏下的位置
   - 你会看到一个灰色的占位框

4. 点击 **"Edit"** → **"Upload an image"**

5. 选择你做好的 1280×640 的 PNG 图片

6. 裁剪预览确认后，点击 **"Save"**

7. 完成！现在任何人分享你的 GitHub 链接都会显示这张图片

### 验证方法

设置后，用以下方式验证：
- 在微信/QQ 中发送 `https://github.com/xyva-yuangui/XyvaClaw` 看预览卡片
- 在 Twitter 发推测试
- 使用 https://www.opengraph.xyz/ 输入你的 GitHub URL 查看预览效果

> 💡 注意：社交平台有缓存，设置后可能需要 5-30 分钟才能看到新图片。Twitter 可以用 https://cards-dev.twitter.com/validator 刷新缓存。

---

## 总结

```
1. 用 Canva 做一张 1280×640 的宣传图
2. 打开 GitHub 仓库 → Settings → Social preview → Upload
3. 保存即可
```

这个 5 分钟就能搞定，但对推广效果的提升非常大 — 因为一张好看的预览图能让分享链接的点击率提高 2-3 倍。
