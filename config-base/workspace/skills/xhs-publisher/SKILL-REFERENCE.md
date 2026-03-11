---
name: xhs-publisher
version: 1.0.0
description: |
  小红书统一发布引擎。自动检测可用发布通道（CDP → Cookie → 降级提示），
  支持单篇/批量发布、多账号矩阵、防封策略。
  合并原 auto-redbook-skills(发布部分)、xiaohongshu-cdp、xhs-batch-operator 三个技能的发布功能。
status: stable
platform: [darwin, linux]
dependencies:
  skills: [xhs-creator]
  bins: [python3]
  python: [requests, websockets, playwright]
metadata:
  openclaw:
    emoji: "🚀"
---

# 小红书统一发布引擎 (xhs-publisher)

> 合并自: auto-redbook-skills(发布) + xiaohongshu-cdp + xhs-batch-operator

统一的小红书发布系统，自动选择最优发布通道：

```
发布请求 → 通道检测(CDP优先 → Cookie备选 → 降级提示) → 执行发布 → 结果确认
```

---

## 发布通道优先级

| 通道 | 方式 | 优势 | 适用场景 |
|------|------|------|---------|
| **CDP** (首选) | Chrome DevTools Protocol | 接近真人操作，不易被风控 | 日常发布 |
| **Cookie** (备选) | API + Cookie | 无需浏览器，速度快 | 批量发布 |
| **手动提示** (降级) | 输出文件，提示手动发布 | 零风险 | Cookie/CDP 均不可用时 |

系统自动检测：CDP 登录状态 → Cookie 有效性 → 降级到手动模式。

---

## 快速开始

### 1. 首次登录（CDP 方式，推荐）

```bash
cd ~/.openclaw/workspace/skills/xhs-publisher
python scripts/cdp_publish.py login
```
弹出浏览器后，用小红书 App 扫码登录。Profile 持久保存，无需反复登录。

### 2. 检查登录/通道状态

```bash
python scripts/xhs_publish.py --check
```
输出所有可用通道的状态。

### 3. 单篇发布

```bash
# 自动选择通道
python scripts/xhs_publish.py \
  --title "标题" \
  --content "正文" \
  --images cover.png card_1.png card_2.png

# 指定 CDP 通道 + 无头模式
python scripts/xhs_publish.py --channel cdp --headless \
  --title "标题" --content "正文" --images cover.png card_1.png

# 指定 Cookie 通道
python scripts/xhs_publish.py --channel cookie \
  --title "标题" --content "正文" --images cover.png card_1.png

# 预览模式（不实际发布）
python scripts/xhs_publish.py --preview \
  --title "标题" --content "正文" --images cover.png

# 从文件读取
python scripts/xhs_publish.py --headless \
  --title-file title.txt --content-file content.txt --images cover.png
```

### 4. 批量发布

```bash
# 批量生成并发布（3 篇）
python scripts/batch_publish.py -n 3 --publish

# 仅生成不发布（审核后手动触发）
python scripts/batch_publish.py -n 3 --no-publish

# 指定主题
python scripts/batch_publish.py \
  -t "租房避坑,理财入门,职场生存" \
  -s 干货 --publish

# 多账号矩阵
python scripts/batch_publish.py -n 5 --publish --account 2
```

---

## 完整参数

### 单篇发布参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--title` | 笔记标题 | 必填 |
| `--content` | 笔记正文 | 必填 |
| `--images` | 本地图片路径（可多个） | 必填 |
| `--channel` | 发布通道: auto/cdp/cookie | auto |
| `--headless` | 无头模式（CDP 后台运行） | false |
| `--preview` | 预览模式（不点击发布） | false |
| `--account` | 使用指定账号 | default |
| `--check` | 健康检查：验证通道和配置 | false |

### 批量发布参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-n, --count` | 批量数量 | 3 |
| `-s, --style` | 内容风格（种草/干货/踩坑/教程/分享） | 种草 |
| `-t, --topics` | 主题列表（逗号分隔） | 自动选题 |
| `--theme` | 卡片主题 | default |
| `--publish` | 自动发布 | false |
| `--no-publish` | 仅生成不发布 | false |
| `-d, --delay` | 发布间隔（秒） | 300 |
| `--account` | 使用第几个账号 | 1 |
| `--source` | 选题来源（reddit/weibo/preset） | preset |

---

## 账号管理

### CDP 账号（推荐）

```bash
# 登录
python scripts/cdp_publish.py login

# 检查登录状态
python scripts/cdp_publish.py check-login

# 切换账号
python scripts/cdp_publish.py switch-account

# 列出所有账号
python scripts/cdp_publish.py list-accounts
```

配置文件: `config/accounts.json`
```json
{
  "default_account": "default",
  "accounts": {
    "default": { "alias": "默认账号", "profile_dir": "..." },
    "work": { "alias": "工作账号", "profile_dir": "..." }
  }
}
```

### Cookie 账号

配置文件: `config/.env`
```bash
# 账号 1
XHS_ACCOUNT_NAME_1=主账号
XHS_COOKIE_1=a1=xxx; web_session=xxx; ...

# 账号 2
XHS_ACCOUNT_NAME_2=副账号
XHS_COOKIE_2=...
```

Cookie 获取: 浏览器登录 xiaohongshu.com → F12 → Network → 复制 Cookie

---

## 高级功能

### 搜索笔记
```bash
python scripts/cdp_publish.py search-feeds --keyword "AI 工具"
```

### 获取笔记详情
```bash
python scripts/cdp_publish.py get-feed-detail --feed-id xxx --xsec-token xxx
```

### 发表评论
```bash
python scripts/cdp_publish.py post-comment-to-feed \
  --feed-id xxx --xsec-token xxx --content "写得很实用！"
```

### 抓取内容数据
```bash
python scripts/cdp_publish.py content-data --csv-file data.csv
```

---

## 标签处理

正文最后一行如果是 `#标签` 格式，会自动提取为话题标签（最多 10 个）：

```
正文内容...

#AI 助手 #效率工具 #OpenClaw
```

---

## 防封策略

1. **发布间隔**: 默认 300 秒（5 分钟），建议 ≥10 分钟
2. **账号间延迟**: 随机 60-180 秒
3. **单个失败不影响**: 一个账号失败继续下一个
4. **发布前检查**: 自动验证 Cookie/CDP 登录状态
5. **每日限额**: 建议每账号每日 ≤ 5 篇
6. **新号养号**: 新号建议先手动发布 1-2 周

---

## 输出目录

```
~/.openclaw/workspace/output/xhs-batch/
├── 20260305_020615_职场新人避坑指南/
│   ├── content.md          # Markdown 文案
│   ├── cover.png           # 封面图
│   ├── card_1.png          # 正文卡片 1
│   ├── card_2.png          # 正文卡片 2
│   └── metadata.json       # 元数据（含发布状态）
└── ...
```

---

## 依赖

- Python 3.10+
- Google Chrome（CDP 通道）
- `requests`, `websockets`（CDP 通信）
- `playwright`（Cookie 通道渲染）

---

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| CDP 登录状态丢失 | `python scripts/cdp_publish.py login` 重新扫码 |
| Cookie 失效 | 从浏览器重新复制 Cookie 到 `.env` |
| Chrome 未启动 | 手动启动带调试端口的 Chrome |
| 渲染失败 | 检查 Playwright: `python -m playwright install chromium` |
| 发布被限流 | 增大 `--delay` 间隔，减少单日发布量 |

---

## 注意事项

1. **首次使用需要扫码登录**（CDP 通道）
2. **Cookie 有效期 7-30 天**，失效需重新获取
3. **图片路径必须是绝对路径**
4. **遵守小红书平台规则**
5. **自动发布前建议人工审核**
6. **never 在未经用户确认前完成支付或购买操作**

---

_合并自: auto-redbook-skills(发布功能) + xiaohongshu-cdp + xhs-batch-operator_  
_创建时间: 2026-03_
