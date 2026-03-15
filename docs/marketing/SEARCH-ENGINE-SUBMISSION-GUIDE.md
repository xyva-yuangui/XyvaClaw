# 搜索引擎提交教程 — 让 Google/百度/Bing 收录 xyvaClaw 官网

> 提交后搜索引擎会开始爬取你的网站，通常 1-7 天内开始收录，2-4 周内出现在搜索结果中。

---

## 一、Google Search Console（谷歌）

### 为什么要提交？
Google 是全球最大的搜索引擎，提交后用户搜索 "xyvaClaw"、"AI assistant platform"、"自我进化 AI 助手" 等关键词时，你的官网会出现在搜索结果中。

### 详细步骤

#### Step 1: 打开 Google Search Console
- 访问 https://search.google.com/search-console
- 用你的 Google 账号登录（没有的话先注册一个 Gmail）

#### Step 2: 添加网站
1. 点击左上角的下拉菜单 → 点击 **"添加资源"**
2. 选择 **"网址前缀"** 方式（右边那个）
3. 输入: `https://www.xyvaclaw.com`
4. 点击 **"继续"**

#### Step 3: 验证网站所有权
Google 需要确认你是网站的主人。推荐使用 **HTML 标签方式**：

1. Google 会给你一段代码，类似:
   ```html
   <meta name="google-site-verification" content="一串随机字符" />
   ```
2. 复制这段代码
3. 打开你的官网项目文件 `index.html`（路径: `XyvaClaw-web/index.html` 或 `xyvaclaw/website/index.html`）
4. 把这段代码粘贴到 `<head>` 标签内（和其他 `<meta>` 标签放在一起）
5. 保存文件，构建并部署官网
6. 回到 Google Search Console，点击 **"验证"**

> 💡 如果你的域名在 Cloudflare 或其他 DNS 服务商，也可以选择 "DNS 记录" 方式验证（添加一条 TXT 记录）

#### Step 4: 提交 Sitemap
验证成功后：
1. 左侧菜单点击 **"站点地图"**（Sitemaps）
2. 在输入框中输入: `sitemap.xml`
3. 点击 **"提交"**
4. 状态会显示 "已提交"，等待 Google 处理

#### Step 5: 请求编入索引（加速收录）
1. 在顶部搜索框输入你的官网地址: `https://www.xyvaclaw.com`
2. 点击 **"请求编入索引"**
3. Google 会优先爬取这个页面

### 完成！后续查看
- 1-3 天后回来查看 **"效果"** 页面，可以看到搜索展示次数和点击数
- **"覆盖范围"** 页面可以看到哪些页面已被收录

---

## 二、百度站长平台

### 为什么要提交？
百度是中国最大的搜索引擎，国内用户主要通过百度搜索。

### 详细步骤

#### Step 1: 注册/登录
- 访问 https://ziyuan.baidu.com/
- 用百度账号登录（没有的话先注册）

#### Step 2: 添加网站
1. 点击顶部 **"用户中心"** → **"站点管理"**
2. 点击 **"添加网站"**
3. 输入: `https://www.xyvaclaw.com`
4. 站点属性选择: "科技互联网" → "软件工具"
5. 点击 **"下一步"**

#### Step 3: 验证网站所有权
推荐 **HTML 标签验证**：

1. 百度会给你一段代码，类似:
   ```html
   <meta name="baidu-site-verification" content="一串字符" />
   ```
2. 复制这段代码
3. 粘贴到官网 `index.html` 的 `<head>` 标签内
4. 构建并部署官网
5. 回到百度站长平台，点击 **"完成验证"**

#### Step 4: 提交 Sitemap
1. 左侧菜单 → **"普通收录"** → **"sitemap"**
2. 输入: `https://www.xyvaclaw.com/sitemap.xml`
3. 点击 **"提交"**

#### Step 5: 手动提交链接（加速收录）
1. 左侧菜单 → **"普通收录"** → **"手动提交"**
2. 输入以下链接（每行一个）:
   ```
   https://www.xyvaclaw.com
   https://www.xyvaclaw.com/sitemap.xml
   ```
3. 点击 **"提交"**

#### 额外加速：百度推送代码
在官网 `index.html` 的 `</body>` 之前添加自动推送代码：
```html
<script>
(function(){
    var bp = document.createElement('script');
    var curProtocol = window.location.protocol.split(':')[0];
    if (curProtocol === 'https') {
        bp.src = 'https://zz.bdstatic.com/linksubmit/push.js';
    } else {
        bp.src = 'http://push.zhanzhang.baidu.com/push.js';
    }
    var s = document.getElementsByTagName("script")[0];
    s.parentNode.insertBefore(bp, s);
})();
</script>
```

---

## 三、Bing Webmaster Tools（必应）

### 为什么要提交？
Bing 是全球第二大搜索引擎，且 ChatGPT 的联网搜索使用 Bing，提交后有助于被 AI 检索到。

### 详细步骤

#### Step 1: 打开 Bing Webmaster
- 访问 https://www.bing.com/webmasters
- 用微软账号登录（Outlook/Hotmail 等都可以）

#### Step 2: 添加网站（推荐一键导入）
Bing 支持直接从 Google Search Console 导入：
1. 点击 **"从 Google Search Console 导入"**
2. 授权你的 Google 账号
3. 自动导入所有设置

**如果不想关联 Google**，可以手动添加：
1. 选择 **"手动添加网站"**
2. 输入: `https://www.xyvaclaw.com`
3. 验证方式选择 **"HTML Meta 标签"**
4. 百度给你的代码类似:
   ```html
   <meta name="msvalidate.01" content="一串字符" />
   ```
5. 粘贴到官网 `index.html` 的 `<head>` 中
6. 构建部署后点击 **"验证"**

#### Step 3: 提交 Sitemap
1. 左侧菜单 → **"Sitemaps"**
2. 输入: `https://www.xyvaclaw.com/sitemap.xml`
3. 点击 **"提交"**

---

## 四、一次性搞定：验证代码汇总

你需要在官网 `index.html` 的 `<head>` 部分添加 3 行验证代码（具体 content 值在各平台获取）：

```html
<head>
  <!-- 你已有的 meta 标签... -->

  <!-- 搜索引擎验证 -->
  <meta name="google-site-verification" content="你的Google验证码" />
  <meta name="baidu-site-verification" content="你的百度验证码" />
  <meta name="msvalidate.01" content="你的Bing验证码" />
</head>
```

### 操作流程总结

```
1. 打开 Google Search Console → 添加网站 → 获取验证码
2. 打开百度站长平台 → 添加网站 → 获取验证码
3. 打开 Bing Webmaster → 添加网站 → 获取验证码
4. 把 3 个验证码一次性添加到 index.html 的 <head> 中
5. 构建并部署官网（npm run build + git push）
6. 回到 3 个平台分别点击"验证"
7. 验证成功后，在 3 个平台分别提交 sitemap: https://www.xyvaclaw.com/sitemap.xml
```

### 提交后多久能搜到？

| 搜索引擎 | 收录时间 | 排名时间 |
|----------|---------|---------|
| Google | 1-3 天 | 1-4 周 |
| 百度 | 3-7 天 | 2-6 周 |
| Bing | 1-3 天 | 1-4 周 |

> 搜索 `site:www.xyvaclaw.com` 可以查看某个搜索引擎是否已收录你的网站。
