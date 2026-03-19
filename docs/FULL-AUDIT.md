# XyvaClaw 完整审查报告

> 审查日期：2026-03-19  
> 审查范围：全部核心代码、安装流程、配置链路、飞书/钉钉接入  
> 审查视角：小白用户首次安装 + 开发者维护

---

## 一、已发现并修复的问题

### 1.1 百炼 API baseUrl 错误（严重）

| 项目 | 详情 |
|------|------|
| **现象** | Web 对话返回乱码/异常响应；飞书机器人回复内容错乱 |
| **根因** | 百炼有两套 API 端点，必须匹配 key 类型 |
| **修复** | `restore-config.py` 新增 `bailian_base_url()` 自动检测函数 |

**两套端点说明：**

| Key 前缀 | 端点 | 用途 |
|----------|------|------|
| `sk-sp-` | `coding.dashscope.aliyuncs.com/v1` | Coding Plan 专用 |
| `sk-` (普通) | `dashscope.aliyuncs.com/compatible-mode/v1` | 通用模型 |

**影响文件（6处）：**

| 文件 | 修复方式 |
|------|----------|
| `installer/restore-config.py` | 新增 `bailian_base_url()` + env/wizard 两条路径自动检测 |
| `setup-wizard/server/index.js` | 验证端点根据 key 前缀动态选择 |
| `config-base/openclaw.json.template` | 默认保持 `coding.dashscope`（多数用户用 sk-sp-） |
| `config-base/agents/main/agent/models.json` | 同上 |
| `config-base/agents/quant-analyst/agent/models.json` | 同上 |
| `config-base/workspace/skills/knowledge-graph-memory/scripts/kg.py` | 同上 |

### 1.2 飞书 accounts key 不匹配（严重）

| 项目 | 详情 |
|------|------|
| **现象** | Gateway 启动后 Doctor 发出迁移警告 |
| **根因** | 模板用 `accounts.main`，OpenClaw 期望 `accounts.default` |
| **修复** | `openclaw.json.template` + `restore-config.py` 改为 `accounts.default` |

### 1.3 飞书单聊被禁（中等）

| 项目 | 详情 |
|------|------|
| **现象** | 用户无法与机器人私聊 |
| **根因** | `dmPolicy` 默认为 `"pairing"`，需要管理员配对 |
| **修复** | 改为 `"open"` + 添加 `allowFrom: ["*"]` |

### 1.4 飞书群聊被静默丢弃（中等）

| 项目 | 详情 |
|------|------|
| **现象** | 群里 @机器人无响应 |
| **根因** | `groupPolicy` 默认为 `"allowlist"`，但未配置白名单 |
| **修复** | 改为 `"open"` |

### 1.5 Vite 构建失败（中等）

| 项目 | 详情 |
|------|------|
| **现象** | Setup Wizard 前端无法构建 |
| **根因** | `npm install --production` 不装 devDeps（vite/react），且用 `npx vite build` |
| **修复** | 需要 build 时强制 `npm install`（含 devDeps） + 用 `npm run build` |

### 1.6 Dashboard 不知道 token（体验）

| 项目 | 详情 |
|------|------|
| **现象** | 打开 Dashboard 看到令牌输入框，不知道去哪找 |
| **修复** | Gateway 启动后自动从 config 提取并显示 token |

---

## 二、飞书机器人调试记录

### 2.1 问题描述

飞书机器人配置了 App ID 和 App Secret，WebSocket 连接正常，但机器人不回复任何消息。

### 2.2 调试过程

| 步骤 | 方法 | 结果 |
|------|------|------|
| 1 | 检查 gateway.log | WebSocket 连接健康，`ws health ok` 每分钟报告 |
| 2 | Bot 身份验证 | ✅ `ou_7357eef708b986fe8efe45a95eaff0ef` (test-god) |
| 3 | API 发送测试 | ✅ 成功发送消息到"开源版本测试群" |
| 4 | 监控事件到达 | ❌ 零事件，30分钟内无任何 `im.message.receive_v1` |
| 5 | 检查 error log | 空，零报错 |
| 6 | SDK 独立测试 | 用 Lark SDK 创建独立 WSClient，debug 模式 → 零事件 |
| 7 | 检查 app config | `callback_type: "websocket"` ✅，`online_version_id` 存在 |
| 8 | 检查 openclaw config | `dmPolicy: open`, `groupPolicy: open`, `accounts.default` ✅ |

### 2.3 根因

**飞书开放平台未添加 `im.message.receive_v1` 事件订阅。**

WebSocket 长连接模式下，即使连接成功，飞书平台也不会推送未订阅的事件类型。这是平台侧配置，无法通过代码修复。

### 2.4 解决方案

在飞书开放平台完成以下配置后，飞书立即恢复正常：

1. **事件与回调** → 订阅方式选择「使用长连接接收事件」
2. **事件与回调** → 添加事件 → `im.message.receive_v1`
3. **权限管理** → 开通「获取与发送单聊/群组消息」
4. **版本管理与发布** → 创建新版本 → 发布上线

### 2.5 验证结果

```
[feishu] received message from ou_321... in oc_89d... (group)        ✅ 群消息接收
[feishu] dispatch start (session=agent:main:feishu:group:oc_89d...)   ✅ @机器人触发回复
[feishu] Started streaming: cardId=7618907383973448909                ✅ 流式卡片回复
[feishu] received message in oc_4fa... (p2p)                          ✅ 单聊(DM)接收
[feishu] dispatch complete (queuedFinal=true, replies=1)              ✅ 回复完成
```

群消息、单聊、流式回复全部正常。

---

## 三、现存潜在问题（代码遍历发现）

### 3.1 Node.js 版本要求过高

```bash
# xyvaclaw-setup.sh:106
if [ "$NODE_MAJOR" -lt 22 ]; then
    MISSING+=("node (当前 $NODE_VER, 需要 22+)")
```

**问题：** Node 22 要求偏高，许多用户系统自带 Node 18/20。OpenClaw 本身可能只需 Node 18+。  
**建议：** 确认 OpenClaw 的实际最低 Node 版本要求，降低到 18 或 20。

### 3.2 `pip3 install --user` 在 venv 环境下警告

```bash
# xyvaclaw-setup.sh:721
pip3 install --user edge-tts 2>/dev/null
```

**问题：** 如果用户在 Python venv 中，`--user` 会产生警告或失败。`2>/dev/null` 隐藏了错误。  
**建议：** 去掉 `--user` 或先检测是否在 venv 中。

### 3.3 `webchat` 通道在 Wizard UI 中标记为"默认启用"

```jsx
// Channels.jsx:42-48
{
    id: 'webchat',
    name: 'Web Chat',
    status: 'available',
    alwaysOn: true,
}
```

**问题：** `webchat` 不是 OpenClaw 认识的通道 ID。`restore-config.py` 中有 `KNOWN_CHANNELS` 过滤，会跳过 `webchat`，但 Wizard UI 上仍显示"默认启用"，可能误导用户以为 Web Chat 是一个需要配置的通道。  
**建议：** 在 Wizard UI 中说明 Web Chat 通过 Dashboard (localhost:18789) 直接使用，不需要任何配置。或者从通道列表中移除 webchat。

### 3.4 `npm install -g openclaw@latest` 可能需要 sudo

```bash
# xyvaclaw-setup.sh:305
npm install -g openclaw@latest
```

**问题：** 非 nvm 用户全局安装需要 sudo，脚本没有处理这种情况。  
**建议：** 添加 `sudo` 前缀或检测权限并提示。

### 3.5 LaunchAgent plist 硬编码了 openclaw 路径

```bash
# xyvaclaw-setup.sh:787
OPENCLAW_BIN=$(which openclaw 2>/dev/null || echo "/usr/local/bin/openclaw")
```

**问题：** 如果用户用 nvm，`which openclaw` 返回的路径在 nvm shim 下（如 `~/.nvm/versions/node/v22/bin/openclaw`），LaunchAgent 可能找不到这个路径（因为 launchd 不加载 nvm 的 shell 初始化）。  
**建议：** 在 plist 中添加 PATH 环境变量或使用 `/usr/local/bin/openclaw`。

### 3.6 安装完成后发送匿名统计

```bash
# xyvaclaw-setup.sh:824
(curl -sS -m 5 -X POST "https://api.xyvaclaw.com/v1/setup-complete" ...
```

**问题：** 如果 `api.xyvaclaw.com` 不存在或超时，虽然不影响安装，但可能留下一个挂起的后台进程。  
**建议：** 确认域名可达，或改为纯可选。

### 3.7 `sed -i.bak` macOS 兼容性

```bash
# xyvaclaw-setup.sh:497
[ -n "${DEEPSEEK_API_KEY:-}" ] && sed -i.bak "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "$ENV_FILE"
```

**问题：** 如果 API Key 包含 `/` 或 `&` 等特殊字符，`sed` 替换会失败。  
**建议：** 改用 Python 或转义特殊字符。

### 3.8 `restore-config.py` 中 `BUILTIN_PROVIDER_META` 的 bailian `baseUrl` 仍是 `compatible-mode`

```python
# restore-config.py:258-259
'bailian': {
    'baseUrl': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
```

**问题：** 这个 `baseUrl` 只在 wizard 路径中作为 fallback 使用。由于 wizard 路径已有 `bailian_base_url()` 覆盖，此处不影响功能，但与模板默认值（`coding.dashscope`）不一致，可能造成维护混淆。  
**建议：** 改为 `coding.dashscope` 保持一致，或添加注释说明此处会被 `bailian_base_url()` 覆盖。

---

## 四、小白用户安装体验优化方案

### 4.1 当前痛点

| 步骤 | 用户需要做的 | 痛点 |
|------|-------------|------|
| 安装前 | 安装 Node.js 22+, Python 3, ffmpeg | 版本要求高 |
| 配置 API | 获取百炼 API Key | ✅ 可接受 |
| 配置飞书 | 获取 App ID/Secret + **在飞书平台配事件订阅 + 发布版本** | ❌ 步骤多且不直观 |
| 启动后 | 打开 Dashboard，输入 token | ✅ 已修复 |
| 飞书不回复 | 无诊断信息，不知道哪里出错 | ❌ 无反馈 |

### 4.2 最小化配置方案

**目标：用户只需提供 3 个值**

```bash
BAILIAN_API_KEY=sk-sp-xxxxxx      # 百炼 API Key
FEISHU_APP_ID=cli_xxxxx           # 飞书 App ID
FEISHU_APP_SECRET=xxxxxxx         # 飞书 App Secret
```

**代码侧已完成的自动化：**
- ✅ baseUrl 根据 key 前缀自动选择
- ✅ dmPolicy/groupPolicy 自动设为 open
- ✅ allowFrom 自动设为 `["*"]`
- ✅ accounts.default 自动填充
- ✅ gateway token 自动生成并显示
- ✅ 插件自动注册和配置

**仍需用户手动在飞书平台完成的（无法自动化）：**
1. 创建飞书应用 + 添加机器人能力
2. 事件订阅：添加 `im.message.receive_v1`
3. 订阅方式：选择长连接
4. 权限：开通消息读写
5. 发布版本

### 4.3 建议改进

#### 改进 1：安装后飞书连接状态诊断

在 gateway 启动后增加自动诊断，告诉用户飞书是否连接成功、是否收到事件：

```bash
# gateway 启动 10 秒后检查
if grep -q "ws client ready" "$XYVACLAW_HOME/logs/gateway.log"; then
    echo "  ✅ 飞书 WebSocket 连接成功"
    echo "  ⚠️  如果机器人不回复，请确认飞书开放平台已："
    echo "     1. 添加事件 im.message.receive_v1"
    echo "     2. 创建版本并发布上线"
fi
```

#### 改进 2：`xyvaclaw doctor` 诊断命令

创建一个快速诊断脚本，用户遇到问题时只需运行：

```bash
xyvaclaw doctor
```

输出示例：
```
🔍 xyvaClaw 环境检查
  ✅ OpenClaw v2026.3.13
  ✅ Gateway 运行中 (PID: 12345)
  ✅ 百炼 API 有效 (sk-sp-****7224 → coding.dashscope)
  ✅ 模型可用: qwen3.5-plus
  ✅ 飞书 WebSocket 已连接 (bot: test-god)
  ❌ 飞书 0 条消息事件 → 请在飞书平台添加事件订阅
```

#### 改进 3：Wizard UI 简化

- 首屏只显示 API Key 输入框
- 飞书/钉钉配置折叠在"通道配置"中
- 移除 webchat "默认启用"标记（它不是真正的通道）

---

## 五、钉钉接入方案

### 5.1 现有生态

OpenClaw 社区已有成熟的钉钉插件：[@soimy/dingtalk](https://github.com/soimy/openclaw-channel-dingtalk)

- 433 stars, 80 forks
- 支持 Stream 模式（类似飞书 WebSocket，无需公网地址）
- 私聊 + 群聊 + AI 互动卡片
- 多 Agent 绑定

### 5.2 接入方式

在安装脚本中集成钉钉插件安装：

```bash
# 如果用户提供了钉钉凭证
if [ -n "$DINGTALK_APP_KEY" ] && [ -n "$DINGTALK_APP_SECRET" ]; then
    log_info "安装钉钉通道插件..."
    openclaw plugins install @soimy/dingtalk
    
    # 写入配置
    python3 -c "
import json
p = '$XYVACLAW_HOME/.openclaw/openclaw.json'
with open(p) as f: d = json.load(f)
d.setdefault('channels', {})['dingtalk'] = {
    'enabled': True,
    'appKey': '$DINGTALK_APP_KEY',
    'appSecret': '$DINGTALK_APP_SECRET',
    'dmPolicy': 'open',
    'groupPolicy': 'open',
}
allow = d.setdefault('plugins', {}).setdefault('allow', [])
if 'dingtalk' not in allow:
    allow.append('dingtalk')
with open(p, 'w') as f: json.dump(d, f, indent=2)
"
    log_ok "钉钉通道已配置"
fi
```

### 5.3 钉钉平台配置（比飞书简单）

1. https://open-dev.dingtalk.com → 创建企业内部应用
2. 添加「机器人」能力
3. 消息接收模式选 **Stream 模式**
4. 开通消息发送权限
5. 发布应用

**用户只需提供：**
- `DINGTALK_APP_KEY`（与 Client ID 相同）
- `DINGTALK_APP_SECRET`

### 5.4 需要修改的文件

| 文件 | 改动 |
|------|------|
| `xyvaclaw-setup.sh` | 添加钉钉插件安装逻辑 |
| `installer/restore-config.py` | 添加 `DINGTALK_APP_KEY/SECRET` 环境变量处理 |
| `templates/.env.template` | 取消注释钉钉配置项 |
| `setup-wizard/src/pages/Channels.jsx` | 钉钉从 "coming" 改为 "available" + 添加配置字段 |
| `setup-wizard/server/index.js` | 添加钉钉 API 验证端点 |

---

## 六、文件变更清单

### 已修改文件

| 文件 | 修改内容 |
|------|----------|
| `installer/restore-config.py` | 新增 `bailian_base_url()` 自动检测；feishu accounts.main→default；dmPolicy/groupPolicy→open；allowFrom |
| `config-base/openclaw.json.template` | feishu accounts.default + dmPolicy open + allowFrom |
| `setup-wizard/server/index.js` | bailian 验证端点根据 key 前缀动态选择 |
| `setup-wizard/src/pages/Channels.jsx` | 飞书配置步骤更新为 WebSocket 模式 |
| `config-base/agents/main/agent/models.json` | baseUrl 保持 coding.dashscope |
| `config-base/agents/quant-analyst/agent/models.json` | 同上 |
| `config-base/workspace/skills/knowledge-graph-memory/scripts/kg.py` | baseUrl fallback 保持一致 |
| `xyvaclaw-setup.sh` | Gateway 启动后显示 token；飞书配置指南更新 |

---

## 七、验证结果

### Clean Install 测试

```bash
BAILIAN_API_KEY="sk-sp-xxx" FEISHU_APP_ID="cli_xxx" FEISHU_APP_SECRET="xxx" \
  bash xyvaclaw-setup.sh --auto
```

**结果：**
- ✅ 安装完成，零错误
- ✅ `openclaw.json` 生成正确
  - baseUrl: `coding.dashscope.aliyuncs.com/v1`（匹配 sk-sp- key）
  - feishu: `accounts.default`, `dmPolicy: open`, `allowFrom: ["*"]`
- ✅ Gateway 启动零 Doctor 警告
- ✅ Gateway token 正确显示
- ✅ 模型 API 调用正常（qwen3.5-plus 响应 OK）
- ✅ 飞书 WebSocket 连接成功
- ✅ 飞书群消息、单聊、流式回复全部正常
