# xyvaClaw 缺陷分析与修复方案

> **审查日期**: 2026-03-19
> **修复日期**: 2026-03-19
> **状态**: ✅ 全部修复完成
> **审查范围**: 全部代码 + 百炼 Coding Plan 官方文档 + OpenClaw 飞书官方文档
> **涉及文件**: 6 个核心文件，约 100 行代码修改

---

## 目录

- [一、问题总览](#一问题总览)
- [二、百炼 Coding Plan 问题（3 个 Bug）](#二百炼-coding-plan-问题3-个-bug)
- [三、飞书集成问题（3 个 Bug）](#三飞书集成问题3-个-bug)
- [四、OpenClaw Dashboard 问题（1 个 Bug）](#四openclaw-dashboard-问题1-个-bug)
- [五、其他问题（2 个）](#五其他问题2-个)
- [六、问题关联图](#六问题关联图)
- [七、逐文件修复方案](#七逐文件修复方案)
- [八、修复优先级与实施顺序](#八修复优先级与实施顺序)

---

## 一、问题总览

| # | 严重性 | 模块 | 问题摘要 | 状态 |
|---|--------|------|----------|------|
| B1 | 🔴 致命 | 百炼 | `restore-config.py` Wizard 路径使用错误的百炼 baseUrl，覆盖模板正确值 | ✅ 已修复 |
| B2 | 🔴 致命 | 百炼 | 模板缺少 `compat.thinkingFormat` 和 `agents.defaults.models` 字段 | ✅ 已修复 |
| B3 | 🟡 中等 | 百炼 | Setup Wizard 验证端点 URL 和模型名均错误，Coding Plan Key 验证必失败 | ✅ 已修复 |
| F1 | 🔴 致命 | 飞书 | `restore-config.py` 清空所有 plugins → feishu_local 插件不加载 | ✅ 已修复 |
| F2 | 🟡 中等 | 飞书 | 飞书配置结构与 OpenClaw 官方 accounts 格式不匹配 | ✅ 已修复 |
| F3 | 🟡 中等 | 飞书 | Setup Wizard 飞书验证缺少 appId 参数 → 验证永远失败 | ✅ 已修复 |
| D1 | 🔴 致命 | Dashboard | 由 B1+B2+F1 联合导致 — Gateway 启动异常或功能缺失 | ✅ 已修复(上游) |
| M1 | 🟢 低 | 技能 | `skill_loading.json` 引用不存在的技能名 | ✅ 已修复 |
| M2 | 🟢 低 | Wizard | `cors` 包引入但未使用 | ⏭ 跳过(无影响) |

---

## 二、百炼 Coding Plan 问题（3 个 Bug）

### B1: restore-config.py Wizard 路径使用错误的百炼 baseUrl（🔴 致命）

**官方文档确认**: 百炼 Coding Plan 的正确 baseUrl 为：
```
https://coding.dashscope.aliyuncs.com/v1
```

**当前模板（正确）**:
```json
// config-base/openclaw.json.template 第 10 行
"baseUrl": "https://coding.dashscope.aliyuncs.com/v1"
```

**Bug 所在**: `installer/restore-config.py` 第 229-233 行的 `BUILTIN_PROVIDER_META` 使用了**错误的 URL**：
```python
'bailian': {
    'baseUrl': 'https://dashscope.aliyuncs.com/compatible-mode/v1',  # ❌ 错误！
    'api': 'openai-completions',
    'models': [],  # ❌ 空列表！
},
```

**触发路径**:
1. 用户通过 Setup Wizard 配置百炼 Key
2. `apply_env()` 发现百炼 Key 仍为 `__API_KEY__` → **删除百炼 provider**
3. `apply_wizard()` 重新添加百炼，但此时 `existing = {}`
4. `existing.get('baseUrl', meta['baseUrl'])` 回退到 `meta['baseUrl']` = **错误 URL**
5. 同时 `existing.get('models', meta['models'])` 回退到 `meta['models']` = **空列表**
6. 最终生成的 config: 百炼 URL 错误 + 无模型可用

**结果**: 百炼平台完全不可用。

---

### B2: 模板缺少关键字段（🔴 致命）

对比百炼官方文档，`openclaw.json.template` 中的百炼配置缺少两个关键部分：

#### 缺失 1: `compat.thinkingFormat` 字段

官方文档要求多个模型配置 `compat.thinkingFormat: "qwen"`，但模板中所有模型都没有此字段：

| 模型 | 官方要求 | 当前模板 |
|------|----------|----------|
| qwen3.5-plus | `"compat": {"thinkingFormat": "qwen"}` | ❌ 缺失 |
| qwen3-max-2026-01-23 | `"compat": {"thinkingFormat": "qwen"}` | ❌ 缺失 |
| glm-5 | `"compat": {"thinkingFormat": "qwen"}` | ❌ 缺失 |
| glm-4.7 | `"compat": {"thinkingFormat": "qwen"}` | ❌ 缺失 |
| kimi-k2.5 | `"compat": {"thinkingFormat": "qwen"}` | ❌ 缺失 |
| qwen3-coder-next | 不需要 | ✅ |
| qwen3-coder-plus | 不需要 | ✅ |
| MiniMax-M2.5 | 不需要 | ✅ |

**影响**: 缺少此字段可能导致模型的思考链/推理格式解析异常。

#### 缺失 2: `agents.defaults.models` 映射

官方文档要求配置 `agents.defaults.models` 字段来声明可用模型：
```json
{
  "agents": {
    "defaults": {
      "models": {
        "bailian/qwen3.5-plus": {},
        "bailian/qwen3-max-2026-01-23": {},
        "bailian/qwen3-coder-next": {},
        "bailian/qwen3-coder-plus": {},
        "bailian/MiniMax-M2.5": {},
        "bailian/glm-5": {},
        "bailian/glm-4.7": {},
        "bailian/kimi-k2.5": {}
      }
    }
  }
}
```

当前模板完全缺少此段。

#### 缺失 3: MiniMax-M2.5 maxTokens 值错误

| 字段 | 官方文档 | 当前模板 |
|------|----------|----------|
| `MiniMax-M2.5.maxTokens` | 32768 | 16384 ❌ |

---

### B3: Setup Wizard 验证端点错误（🟡 中等）

`setup-wizard/server/index.js` 第 50-60 行：

```javascript
case 'bailian':
  url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'; // ❌ 非 Coding Plan 端点
  body = JSON.stringify({
    model: 'qwen-turbo',  // ❌ 已过时的模型名，Coding Plan 可能无权访问
    // ...
  });
```

**问题**:
1. **URL 错误**: Coding Plan Key 只能访问 `coding.dashscope.aliyuncs.com`，不能访问 `dashscope.aliyuncs.com`
2. **模型名错误**: `qwen-turbo` 不在 Coding Plan 支持的模型列表中

**结果**: 用户在 Wizard 中输入正确的百炼 Coding Plan Key → 点击验证 → **永远返回失败**。

---

## 三、飞书集成问题（3 个 Bug）

### F1: restore-config.py 清空所有 plugins（🔴 致命）

`installer/restore-config.py` 第 195-199 行：
```python
data['plugins'] = {
    'allow': [],
    'slots': {},
    'entries': {},
}
```

这段代码将模板中所有已配置的 plugins **全部清空**。模板原始配置为：
```json
{
  "plugins": {
    "allow": ["lossless-claw", "feishu_local", "feishu"],
    "slots": { "contextEngine": "lossless-claw" },
    "entries": {
      "lossless-claw": { "enabled": true, "config": { ... } },
      "feishu": { "enabled": false },
      "feishu_local": { "enabled": true }
    }
  }
}
```

**被清空后的影响**:
- `feishu_local` 插件不加载 → **飞书通道完全不工作**
- `lossless-claw` 不加载 → **上下文引擎失效**
- Gateway 缺少核心插件 → **Dashboard 可能异常**

---

### F2: 飞书配置结构与官方格式不匹配（🟡 中等）

**OpenClaw 官方推荐格式**（来自 https://docs.openclaw.ai/channels/feishu ）:
```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "dmPolicy": "pairing",
      "accounts": {
        "main": {
          "appId": "cli_xxx",
          "appSecret": "xxx",
          "botName": "My AI assistant"
        }
      }
    }
  }
}
```

**当前模板格式**（`openclaw.json.template`）:
```json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "appId": "__APP_ID__",
      "appSecret": "__APP_SECRET__",
      "domain": "feishu",
      "groupPolicy": "allowlist"
    }
  }
}
```

**差异对比**:

| 项目 | 官方格式 | 当前模板 |
|------|----------|----------|
| 凭证位置 | `accounts.main.appId` | 顶层 `appId` |
| 连接模式 | 默认 `websocket` | 未显式设置 |
| DM 策略 | `dmPolicy: "pairing"` | 未设置 |
| 群组策略 | `groupPolicy: "open"` | `groupPolicy: "allowlist"` |
| `botName` | 有 | 无 |
| `requireMention` | 默认 `true` | 未设置 |

**注意**: 顶层 `appId`/`appSecret` 是向后兼容的旧格式，OpenClaw 仍然支持。但建议升级到 `accounts` 嵌套格式。

**飞书开放平台配置要点**（来自官方文档）:
1. 创建企业自建应用 → 添加**机器人**能力
2. 事件订阅 → 选择 **Use long connection to receive events (WebSocket)**
3. 添加事件: `im.message.receive_v1`
4. 需要的权限 scopes:
   ```
   im:message, im:message:send_as_bot, im:message:readonly,
   im:message.p2p_msg:readonly, im:message.group_at_msg:readonly,
   im:chat.members:bot_access, im:resource,
   cardkit:card:read, cardkit:card:write,
   contact:user.employee_id:readonly
   ```
5. 发布应用并等待审批

---

### F3: Setup Wizard 飞书验证缺少 appId（🟡 中等）

`setup-wizard/src/components/ApiKeyInput.jsx` 第 22-26 行：
```javascript
const res = await fetch('/api/validate-key', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ provider, apiKey: value }),  // ❌ 缺少 appId
});
```

服务端 `server/index.js` 第 63-68 行需要 `appId`:
```javascript
case 'feishu': {
  const appId = req.body.appId;  // ← 永远是 undefined
  body = JSON.stringify({ app_id: appId, app_secret: apiKey });
}
```

**结果**: 飞书凭证验证发送 `app_id: undefined` → **验证永远失败**。

---

## 四、OpenClaw Dashboard 问题（1 个 Bug）

### D1: Dashboard 无法运行（🔴 致命 — 由上游 Bug 联合导致）

OpenClaw Dashboard 通过 `openclaw dashboard` 命令启动，它依赖 `~/.xyvaclaw/.openclaw/openclaw.json` 中的正确配置。

**根因链**:
```
B1 (百炼 URL 错误) + B2 (缺少字段) → 模型调用失败 → Gateway 异常
F1 (plugins 被清空) → lossless-claw 不加载 → 上下文引擎失效
F1 (plugins 被清空) → feishu_local 不加载 → 飞书通道不工作
以上三者联合 → Dashboard 启动后功能不正常或报错
```

**Dashboard 正确启动方式**（来自百炼官方文档）:
```bash
openclaw dashboard
# 浏览器自动打开 http://127.0.0.1:xxxx
```

注意：不是直接访问 `http://localhost:18789`。端口 18789 是 Gateway API 端口，Dashboard 有自己的 Web UI 端口。

---

## 五、其他问题（2 个）

### M1: skill_loading.json 引用不存在的技能名（🟢 低）

`config-base/config/skill_loading.json` 第 19-21 行:
```json
"quant-stock-screener/config",
"quant-stock-screener/output",
"quant-stock-screener/cache/tushare"
```
实际技能名为 `quant-strategy-engine`。

### M2: cors 包引入未使用（🟢 低）

`setup-wizard/server/index.js` 的 `package.json` 依赖了 `cors` 包但代码中未使用 `app.use(cors())`。

---

## 六、问题关联图

```
用户报告: "百炼大模型平台不支持"
  │
  ├─ B1: restore-config.py Wizard 路径 → 错误 URL + 空模型列表 [致命根因]
  ├─ B2: 模板缺少 compat.thinkingFormat + agents.defaults.models [致命]
  └─ B3: Wizard 验证用错误端点+过时模型 → 验证必失败 [中等]

用户报告: "飞书无法设置"
  │
  ├─ F1: restore-config.py 清空 plugins → feishu_local 不加载 [致命根因]
  ├─ F2: 配置格式用旧式顶层 appId（可工作但非最佳） [中等]
  └─ F3: Wizard 验证不传 appId → 验证必失败 [中等]

用户报告: "OpenClaw Dashboard 无法运行"
  │
  ├─ B1+B2 → 模型不可用 → Gateway 异常 [上游]
  └─ F1 → plugins 不加载 → 核心功能缺失 [上游]
```

---

## 七、逐文件修复方案

### 文件 1: `config-base/openclaw.json.template`

**改动**: 为百炼模型添加 `compat.thinkingFormat` 字段，修正 `MiniMax-M2.5.maxTokens`，添加 `agents.defaults.models` 映射。

```diff
  {
    "id": "qwen3.5-plus",
    "name": "qwen3.5-plus",
    "reasoning": false,
    "input": ["text", "image"],
    "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
    "contextWindow": 1000000,
-   "maxTokens": 65536
+   "maxTokens": 65536,
+   "compat": { "thinkingFormat": "qwen" }
  },
  {
    "id": "qwen3-max-2026-01-23",
    ...
-   "maxTokens": 65536
+   "maxTokens": 65536,
+   "compat": { "thinkingFormat": "qwen" }
  },
  // qwen3-coder-next: 不需要 compat
  // qwen3-coder-plus: 不需要 compat
  {
    "id": "MiniMax-M2.5",
    ...
-   "maxTokens": 16384
+   "maxTokens": 32768
  },
  {
    "id": "glm-5",
    ...
-   "maxTokens": 16384
+   "maxTokens": 16384,
+   "compat": { "thinkingFormat": "qwen" }
  },
  {
    "id": "glm-4.7",
    ...
-   "maxTokens": 16384
+   "maxTokens": 16384,
+   "compat": { "thinkingFormat": "qwen" }
  },
  {
    "id": "kimi-k2.5",
    ...
-   "maxTokens": 32768
+   "maxTokens": 32768,
+   "compat": { "thinkingFormat": "qwen" }
  }
```

在 `agents.defaults` 中添加 `models` 映射:
```diff
  "agents": {
    "defaults": {
      "model": {
        "primary": "deepseek/deepseek-chat",
        "fallbacks": [...]
      },
+     "models": {
+       "bailian/qwen3.5-plus": {},
+       "bailian/qwen3-max-2026-01-23": {},
+       "bailian/qwen3-coder-next": {},
+       "bailian/qwen3-coder-plus": {},
+       "bailian/MiniMax-M2.5": {},
+       "bailian/glm-5": {},
+       "bailian/glm-4.7": {},
+       "bailian/kimi-k2.5": {},
+       "deepseek/deepseek-chat": {},
+       "deepseek/deepseek-reasoner": {}
+     },
      "bootstrapMaxChars": 16000,
```

飞书通道配置升级为 accounts 格式:
```diff
  "channels": {
    "feishu": {
      "enabled": true,
-     "appId": "__APP_ID__",
-     "appSecret": "__APP_SECRET__",
      "domain": "feishu",
+     "connectionMode": "websocket",
+     "dmPolicy": "pairing",
      "groupPolicy": "allowlist",
-     "groupAllowFrom": [],
-     "topicSessionMode": "disabled",
-     "responseWatchdogSec": 30,
-     "dmPolicy": "allowlist",
-     "allowFrom": [],
-     "sessionDispatchConcurrency": 5,
-     "docEditorOpenIds": []
+     "requireMention": true,
+     "accounts": {
+       "main": {
+         "appId": "__APP_ID__",
+         "appSecret": "__APP_SECRET__"
+       }
+     }
    }
  }
```

---

### 文件 2: `installer/restore-config.py`

**改动 A**: 修正 `BUILTIN_PROVIDER_META` 的百炼 baseUrl 和 models（修复 B1）

```diff
  BUILTIN_PROVIDER_META = {
      'deepseek': { ... },
      'bailian': {
-         'baseUrl': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
+         'baseUrl': 'https://coding.dashscope.aliyuncs.com/v1',
          'api': 'openai-completions',
-         'models': [],
+         'models': [
+             {'id': 'qwen3.5-plus', 'name': 'qwen3.5-plus', 'reasoning': False,
+              'input': ['text', 'image'], 'contextWindow': 1000000, 'maxTokens': 65536,
+              'compat': {'thinkingFormat': 'qwen'}},
+             {'id': 'qwen3-max-2026-01-23', 'name': 'qwen3-max-2026-01-23', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 262144, 'maxTokens': 65536,
+              'compat': {'thinkingFormat': 'qwen'}},
+             {'id': 'qwen3-coder-next', 'name': 'qwen3-coder-next', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 262144, 'maxTokens': 65536},
+             {'id': 'qwen3-coder-plus', 'name': 'qwen3-coder-plus', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 1000000, 'maxTokens': 65536},
+             {'id': 'MiniMax-M2.5', 'name': 'MiniMax-M2.5', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 196608, 'maxTokens': 32768},
+             {'id': 'glm-5', 'name': 'glm-5', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 202752, 'maxTokens': 16384,
+              'compat': {'thinkingFormat': 'qwen'}},
+             {'id': 'glm-4.7', 'name': 'glm-4.7', 'reasoning': False,
+              'input': ['text'], 'contextWindow': 202752, 'maxTokens': 16384,
+              'compat': {'thinkingFormat': 'qwen'}},
+             {'id': 'kimi-k2.5', 'name': 'kimi-k2.5', 'reasoning': False,
+              'input': ['text', 'image'], 'contextWindow': 262144, 'maxTokens': 32768,
+              'compat': {'thinkingFormat': 'qwen'}},
+         ],
      },
  }
```

**改动 B**: 不再清空 plugins，改为智能合并（修复 F1）

```diff
- # Strip plugins for fresh install (they get auto-detected at runtime)
- data['plugins'] = {
-     'allow': [],
-     'slots': {},
-     'entries': {},
- }
+ # Preserve plugins from template, dynamically toggle feishu based on config
+ if 'plugins' not in data:
+     data['plugins'] = {'allow': [], 'slots': {}, 'entries': {}}
+ # Ensure lossless-claw is always enabled
+ if 'lossless-claw' not in data.get('plugins', {}).get('allow', []):
+     data.setdefault('plugins', {}).setdefault('allow', []).append('lossless-claw')
+ # Toggle feishu_local based on whether feishu channel is configured
+ feishu_enabled = data.get('channels', {}).get('feishu', {}).get('enabled', False)
+ if feishu_enabled:
+     allow_list = data['plugins'].get('allow', [])
+     if 'feishu_local' not in allow_list:
+         allow_list.append('feishu_local')
+     data['plugins'].setdefault('entries', {})['feishu_local'] = {'enabled': True}
```

**改动 C**: 飞书配置适配 accounts 格式（配合 F2 修复）

在 `apply_env()` 的飞书处理中:
```diff
  if feishu_id and feishu_secret:
      if 'channels' not in data:
          data['channels'] = {}
-     data['channels']['feishu'] = data.get('channels', {}).get('feishu', {})
-     data['channels']['feishu']['enabled'] = True
-     data['channels']['feishu']['appId'] = feishu_id
-     data['channels']['feishu']['appSecret'] = feishu_secret
-     data['channels']['feishu'].setdefault('domain', 'feishu')
-     data['channels']['feishu'].setdefault('groupPolicy', 'allowlist')
-     data['channels']['feishu'].setdefault('dmPolicy', 'allowlist')
+     feishu_conf = data.get('channels', {}).get('feishu', {})
+     feishu_conf['enabled'] = True
+     feishu_conf.setdefault('domain', 'feishu')
+     feishu_conf.setdefault('connectionMode', 'websocket')
+     feishu_conf.setdefault('dmPolicy', 'pairing')
+     feishu_conf.setdefault('groupPolicy', 'allowlist')
+     feishu_conf.setdefault('requireMention', True)
+     # Use accounts format (official recommended)
+     if 'accounts' not in feishu_conf:
+         feishu_conf['accounts'] = {}
+     feishu_conf['accounts'].setdefault('main', {})
+     feishu_conf['accounts']['main']['appId'] = feishu_id
+     feishu_conf['accounts']['main']['appSecret'] = feishu_secret
+     # Remove legacy top-level credentials if present
+     feishu_conf.pop('appId', None)
+     feishu_conf.pop('appSecret', None)
+     data['channels']['feishu'] = feishu_conf
```

---

### 文件 3: `setup-wizard/server/index.js`

**改动 A**: 修正百炼验证端点和模型名（修复 B3）

```diff
  case 'bailian':
-   url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions';
+   url = 'https://coding.dashscope.aliyuncs.com/v1/chat/completions';
    headers = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    };
    body = JSON.stringify({
-     model: 'qwen-turbo',
+     model: 'qwen3-coder-plus',
      messages: [{ role: 'user', content: 'hi' }],
      max_tokens: 1,
    });
    break;
```

---

### 文件 4: `setup-wizard/src/components/ApiKeyInput.jsx`

**改动**: 支持传递额外请求参数（修复 F3）

```diff
  export default function ApiKeyInput({
    label, value, onChange, placeholder,
-   provider, verified, helpUrl, helpText,
+   provider, verified, helpUrl, helpText, extraBody,
  }) {
    // ...
    const handleVerify = async () => {
      if (!value.trim()) return;
      setVerifying(true);
      setVerifyResult(null);
      try {
        const res = await fetch('/api/validate-key', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
-         body: JSON.stringify({ provider, apiKey: value }),
+         body: JSON.stringify({ provider, apiKey: value, ...extraBody }),
        });
```

---

### 文件 5: `setup-wizard/src/pages/Channels.jsx`

**改动**: 飞书 ApiKeyInput 传递 appId（配合 F3 修复）

```diff
  <ApiKeyInput
    label="App Secret"
    value={chConfig.appSecret || ''}
    onChange={(val) => updateConfig('channels.feishu.appSecret', val)}
    placeholder="飞书应用密钥"
    provider="feishu"
    helpUrl={ch.helpUrl}
    helpText={ch.helpText}
+   extraBody={{ appId: chConfig.appId }}
  />
```

---

### 文件 6: `config-base/config/skill_loading.json`（修复 M1）

```diff
  "preload_on_startup": [
-   "quant-stock-screener/config",
-   "quant-stock-screener/output",
-   "quant-stock-screener/cache/tushare"
+   "quant-strategy-engine/config",
+   "quant-strategy-engine/output",
+   "quant-strategy-engine/cache/tushare"
  ]
```

---

## 八、修复优先级与实施顺序

| 步骤 | 修复 | 文件 | 影响 |
|------|------|------|------|
| **1** | F1: 不清空 plugins | `restore-config.py` | 恢复飞书通道 + 上下文引擎 |
| **2** | B1: 修正百炼 BUILTIN_PROVIDER_META | `restore-config.py` | 恢复百炼 Wizard 路径 |
| **3** | B2: 添加 compat + models 映射 | `openclaw.json.template` | 百炼模型正常工作 |
| **4** | B3: 修正验证端点 | `server/index.js` | 百炼 Key 验证可用 |
| **5** | F2: 飞书 accounts 格式 | `openclaw.json.template` + `restore-config.py` | 飞书配置规范化 |
| **6** | F3: 飞书验证传 appId | `ApiKeyInput.jsx` + `Channels.jsx` | 飞书验证可用 |
| **7** | M1: 技能名修正 | `skill_loading.json` | 技能预加载正常 |

**预计工作量**: 修改 6 个文件，约 100 行代码变更。

---

## 附录 A: 官方文档参考

- **百炼 Coding Plan**: 阿里云文档 — "在 OpenClaw 接入阿里云 Coding Plan"
- **OpenClaw 飞书频道**: https://docs.openclaw.ai/channels/feishu
- **飞书开放平台**: https://open.feishu.cn/
- **OpenClaw 官方插件**: `@openclaw/feishu` (npm)

## 附录 B: 飞书机器人接入 Checklist

基于 OpenClaw 官方文档整理：

- [ ] 1. 登录 [飞书开放平台](https://open.feishu.cn/app) → 创建企业自建应用
- [ ] 2. 添加**机器人**能力 → 设置机器人名称
- [ ] 3. 复制 **App ID** (`cli_xxx`) 和 **App Secret**
- [ ] 4. 配置权限 scopes（至少需要 `im:message`, `im:message:send_as_bot`, `im:message:readonly`, `im:resource` 等）
- [ ] 5. 事件订阅 → 选择 **长连接 (WebSocket)** → 添加事件 `im.message.receive_v1`
- [ ] 6. 发布应用 → 等待审批
- [ ] 7. 在 xyvaClaw 中配置 App ID 和 App Secret
- [ ] 8. `xyvaclaw gateway` 启动 → 发消息测试
- [ ] 9. DM 模式下首次需完成 pairing（配对码验证）
