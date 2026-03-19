# 飞书应用配置指南

> 从零开始创建飞书机器人并连接 xyvaClaw

---

## 前提条件

- 一个飞书企业账号（个人版也可以创建应用）
- xyvaClaw 已安装并可运行
- 你的服务器/电脑有公网 IP 或内网穿透（用于接收飞书回调）

---

## Step 1: 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 点击右上角「创建应用」→ 选择「企业自建应用」
3. 填写应用名称（如 "xyvaClaw AI"）和描述
4. 创建完成后进入应用管理页面

## Step 2: 获取凭证

1. 在应用管理页面，进入「凭证与基础信息」
2. 记录以下信息：
   - **App ID**: `cli_xxxxxxxxxxxx`
   - **App Secret**: 点击显示并复制

这两个值填入 xyvaClaw 配置向导的飞书通道配置中。

## Step 3: 添加机器人能力

1. 左侧菜单 →「应用能力」→「添加应用能力」
2. 选择「机器人」
3. 确认添加

## Step 4: 配置权限

左侧菜单 →「权限管理」，开通以下权限：

### 必需权限

| 权限 | API Name | 用途 |
|------|----------|------|
| 获取与发送单聊、群组消息 | `im:message` | 收发消息 |
| 读取用户发给机器人的单聊消息 | `im:message.receive_event` | 接收消息事件 |
| 以应用身份发消息 | `im:message:send_as_bot` | 发送消息 |
| 获取群组信息 | `im:chat:readonly` | 读取群信息 |
| 获取用户基本信息 | `contact:user.base:readonly` | 识别用户 |

### 推荐权限（启用更多功能）

| 权限 | API Name | 用途 |
|------|----------|------|
| 查看、评论、编辑和管理云文档 | `docs:doc` | 文档读写 |
| 查看、评论、编辑和管理电子表格 | `sheets:spreadsheet` | 表格操作 |
| 上传、下载文件 | `drive:drive` | 文件管理 |
| 创建和管理知识库 | `wiki:wiki` | Wiki 操作 |
| 管理日历 | `calendar:calendar` | 日历读写 |
| 管理审批 | `approval:approval` | 审批流程 |

## Step 5: 配置事件订阅

1. 左侧菜单 →「事件与回调」→「事件配置」
2. 点击「添加事件」，订阅以下事件：

| 事件 | Event Name | 用途 |
|------|------------|------|
| 接收消息 | `im.message.receive_v1` | 接收用户消息 |
| 消息已读 | `im.message.message_read_v1` | 消息已读回执 |

3. 配置请求地址：

```
http://你的IP:18789/feishu/webhook
```

> 如果是本地开发，可以用 ngrok/frp 等工具做内网穿透

4. 加密策略：选择「不加密」（简单）或配置 Encrypt Key

## Step 6: 发布应用

1. 左侧菜单 →「版本管理与发布」
2. 创建版本 → 填写版本号和说明
3. 提交审核（企业管理员审核）
4. 审核通过后，应用自动上线

> 开发阶段可以将自己添加为测试用户，无需审核即可使用

## Step 7: 在 xyvaClaw 中配置

### 方式 A: 配置向导

安装时在 Web 向导的「消息通道」页面填写 App ID 和 App Secret。

### 方式 B: 手动配置

编辑 `~/.xyvaclaw/.env`：

```bash
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

飞书 Secret 还需要写入 secrets 文件：

```bash
echo "FEISHU_APP_SECRET=你的Secret" > ~/.xyvaclaw/secrets/feishu.env
chmod 600 ~/.xyvaclaw/secrets/feishu.env
```

## Step 8: 验证连接

```bash
# 启动 gateway
xyvaclaw gateway

# 查看日志，确认飞书连接成功
tail -f ~/.xyvaclaw/logs/gateway.log | grep feishu
```

在飞书中找到你的机器人，发送一条消息。如果收到回复，说明配置成功！

---

## 常见问题

### Q: 回调地址验证失败？
- 确保 gateway 已启动
- 确保端口 18789 可从公网访问
- 检查防火墙规则

### Q: 消息收到但没有回复？
- 检查 `logs/gateway.err.log` 是否有 API key 错误
- 确认至少配置了一个模型 Provider

### Q: 群聊中不回复？
- 默认使用 allowlist 策略，需要添加群 ID 到配置
- 或在 `openclaw.json` 中将 `groupPolicy` 改为 `open`

### Q: 多台机器能用同一个飞书应用吗？
- 不能同时运行。飞书一个应用只有一个 webhook 地址。
- 如需多台，创建多个飞书应用。

---

## 安全建议

- App Secret 不要提交到代码仓库
- 建议启用飞书的 Encrypt Key 加密
- 定期检查应用权限，仅保留必要权限
- 生产环境建议使用 HTTPS（通过反向代理如 Nginx/Caddy）
