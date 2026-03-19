# xyvaClaw 安装方案重新设计

> 目标：小白用户从零到能用，**全程不超过 3 分钟，最多填 1 个值**

---

## 一、当前流程痛点分析

### 用户走完整个流程要做的事

| 步骤 | 动作 | 耗时 | 痛点级别 |
|------|------|------|----------|
| 0 | 安装 Node.js 22+、Python 3、ffmpeg | 5-15min | 🔴 致命 — 很多人卡在这里 |
| 1 | git clone 仓库 | 30s | ✅ 可接受 |
| 2 | 运行 setup.sh | 自动 | ✅ |
| 3 | 选择"Web 向导"还是"手动编辑" | 5s | 🟡 不该有这个选择 |
| 4 | 在 Web 向导里填 API Key | 1min | 🟡 向导启动慢（npm install + vite build） |
| 5 | 等待安装（npm install × N 次） | 3-5min | 🟡 等待时间长 |
| 6 | 安装完成，提示"是否启动 gateway" | 5s | 🟡 不该问 |
| 7 | 打开 Dashboard `localhost:18789` | 5s | ✅ |
| **8** | **看到"请输入网关令牌"输入框** | **???** | **🔴 致命 — 用户不知道令牌在哪里** |
| 9 | 回到终端找令牌、复制、粘贴 | 30s | 🔴 严重挫败感 |
| 10 | 开始对话 | - | ✅ |

**核心问题：步骤 0、8、9 是三座大山。**

### 令牌问题的根因

```json
// openclaw.json.template
"gateway": {
    "auth": {
        "mode": "token",          // ← 强制需要令牌
        "token": "__AUTO_GENERATE__"
    },
    "bind": "loopback"            // ← 但只监听本机
}
```

Gateway 绑定在 `loopback`（127.0.0.1），只有本机能访问。在这种模式下要求令牌是**不必要的安全开销**。

---

## 二、新方案设计

### 核心原则

```
最少输入 → 最快启动 → 最直观反馈
```

### 2.1 理想的用户体验（终极目标）

```bash
# 用户只需执行一行
curl -fsSL https://install.xyvaclaw.com | bash
```

脚本自动：
1. 安装 Node.js（如果没有）
2. 安装 OpenClaw
3. 弹出浏览器 → 只有一个输入框："请粘贴你的 API Key"
4. 用户粘贴 Key → 点"开始"
5. 直接进入对话界面，**没有令牌输入步骤**

### 2.2 近期可实现的方案（本次实施）

#### 改动 1：Gateway 本机免令牌（🔴 最关键）

**原理**：`bind: loopback` 时，只有本机能访问 Dashboard，无需令牌认证。

**实施**：

```python
# restore-config.py 修改
if data['gateway'].get('bind') == 'loopback':
    data['gateway']['auth'] = {'mode': 'none'}
```

**影响**：用户打开 `localhost:18789` 直接看到对话界面，**不再需要输入令牌**。

> 如果用户后续想对外暴露（tailscale、公网），再手动开启 token 认证。

#### 改动 2：安装流程直线化（去掉所有分叉）

**Before（当前 8 个 step + 多个 y/n 确认）：**
```
Step 1: 检查环境 → 缺 Node? 报错退出
Step 2: 安装 OpenClaw
Step 3: 部署配置
Step 4: 选 Web 向导还是手动? → 向导要 npm install + vite build...
Step 5: 生成身份文件
Step 6: 安装依赖（npm install × 好多次）
Step 7: 配置环境 → sudo 创建 wrapper? 开机自启?
Step 8: 启动 gateway? → 输入令牌?
```

**After（新 4 步）：**
```
Step 1: 环境检查 + 自动安装缺失依赖（Node/Python/ffmpeg 全自动）
Step 2: 安装 OpenClaw + 部署配置 + 安装所有依赖（一步完成）
Step 3: 弹出浏览器 → 只需填 API Key → 自动生成配置
Step 4: 自动启动 Gateway → 自动打开 Dashboard → 直接对话
```

**零确认、零选择、零令牌。**

#### 改动 3：API Key 输入极简化

**方式 A — 环境变量（高级用户）：**
```bash
BAILIAN_API_KEY=sk-sp-xxx bash xyvaclaw-setup.sh
```

**方式 B — 安装时交互式提问（小白用户）：**
```
请粘贴你的 API Key（从 bailian.console.aliyun.com 获取）:
> sk-sp-0e18bc017d6748c985ac273e47701224
✅ API Key 有效（百炼 Coding Plan → qwen3.5-plus 可用）
```

脚本自动：
- 检测 key 类型（sk-sp- / sk- / sk-xxx deepseek）
- 选择正确的 baseUrl
- 验证 key 可用（发一个 test 请求）
- 写入配置

**不再需要 Web 向导**，也不再需要手动编辑 .env。

#### 改动 4：依赖安装自动化（macOS）

```bash
# 当前：报错退出
if [ "$NODE_MAJOR" -lt 22 ]; then
    MISSING+=("node")  # 然后退出
fi

# 改为：自动安装
if [ "$NODE_MAJOR" -lt 22 ]; then
    log_info "安装 Node.js 22..."
    if command -v brew &>/dev/null; then
        brew install node@22
    else
        # 使用 nvm 或官方安装包
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
        nvm install 22
    fi
fi
```

#### 改动 5：去掉 Web 向导的构建步骤

Web 向导需要 npm install + vite build，耗时 1-3 分钟且容易失败。

**方案**：直接在终端交互式问 API Key（只问一个问题），或者在 `dist/` 中预构建好（已在 repo 中）。

**对于小白用户**，终端直接问比打开浏览器更简单：

```bash
echo "请粘贴你的 API Key:"
read -r API_KEY
# 自动检测类型、验证、写入
```

#### 改动 6：自动打开 Dashboard 并跳过令牌

```bash
# 启动 gateway 后
open "http://localhost:18789"  # 因为 auth mode=none，直接进入对话
```

---

## 三、新旧对比

### 小白用户体验对比

| 维度 | 当前方案 | 新方案 |
|------|----------|--------|
| **用户需要输入的值** | API Key + 网关令牌 + 多个 y/n | **只输入 API Key** |
| **用户需要做的选择** | Web向导/手动、是否sudo、是否自启、是否启动 | **零选择** |
| **Node.js 版本** | 需要手动安装 22+ | **自动安装** |
| **从 clone 到能用** | 8-15 分钟 | **3 分钟** |
| **首次打开 Dashboard** | 看到令牌输入框，懵 | **直接看到对话界面** |
| **飞书配置** | 安装时就要填 | **安装后按需配置** |

### 新安装流程（完整）

```
$ git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh

  ██╗  ██╗██╗   ██╗██╗   ██╗ █████╗  ██████╗██╗      █████╗ ██╗    ██╗
  ...

[1/4] 检查环境...
  ✅ macOS 15.3
  ℹ  Node.js 未安装，正在安装...
  ✅ Node.js 22.14.0 (via nvm)
  ✅ Python 3.12
  ✅ ffmpeg 7.1

[2/4] 安装 xyvaClaw...
  ✅ OpenClaw 运行时
  ✅ 配置文件 + 38 个技能
  ✅ 飞书扩展 + 无损上下文引擎
  ✅ Python 依赖

[3/4] 配置 AI 模型...

  请粘贴你的 API Key
  （获取地址：https://bailian.console.aliyun.com → API-KEY 管理 → 创建）
  
  > sk-sp-0e18bc017d6748c985ac273e47701224
  
  ✅ 百炼 Coding Plan 密钥有效
  ✅ 可用模型: qwen3.5-plus, qwen3-max, kimi-k2.5

[4/4] 启动...
  ✅ Gateway 已启动
  ✅ 正在打开浏览器...

  🎉 安装完成！打开的浏览器页面就是你的 AI 助手。
  
  想接入飞书？运行: xyvaclaw setup feishu
  文档: https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FEISHU-SETUP.md
```

---

## 四、需要修改的文件

### 4.1 必须改（解决令牌问题 + 流程简化）

| 文件 | 改动 | 优先级 |
|------|------|--------|
| `installer/restore-config.py` | `bind=loopback` 时 `auth.mode='none'` | P0 |
| `xyvaclaw-setup.sh` | 重构安装流程为 4 步；加入 API Key 交互式输入 + 自动验证；去掉所有 y/n 确认；自动安装 Node.js | P0 |
| `config-base/openclaw.json.template` | `auth.mode` 改为 `none`（默认值） | P0 |

### 4.2 建议改（体验优化）

| 文件 | 改动 | 优先级 |
|------|------|--------|
| `xyvaclaw-setup.sh` | 合并所有 npm install 为一步 | P1 |
| `xyvaclaw-setup.sh` | 去掉 Web 向导路径（直接终端问 Key） | P1 |
| `xyvaclaw-setup.sh` | sudo wrapper 不需要确认（或用 npx 替代） | P2 |
| `setup-wizard/` | 可选保留，但不是默认路径 | P2 |

### 4.3 后续改（飞书专项）

| 文件 | 改动 | 优先级 |
|------|------|--------|
| 新增 `xyvaclaw setup feishu` 子命令 | 独立的飞书配置向导 | P1 |
| 新增 `docs/FEISHU-SETUP.md` | 带截图的飞书配置教程 | P1 |

---

## 五、Gateway Auth 方案详细说明

### 为什么可以关闭本地认证

| 条件 | 当前配置 | 安全分析 |
|------|----------|----------|
| `bind` | `loopback` (127.0.0.1) | 只有本机进程能访问 |
| 攻击面 | 恶意网页 CSRF | OpenClaw Gateway 不执行危险操作，且有 CORS 保护 |
| 同类产品 | Ollama、LM Studio、Continue.dev | **全部默认无认证** |

### 认证分级方案

```
本地模式 (bind: loopback)  → auth: none     ← 默认
内网模式 (bind: 0.0.0.0)   → auth: token    ← 需要用户手动开启
公网模式 (tailscale/ngrok)  → auth: token    ← 必须
```

### 实现代码

```python
# restore-config.py
bind = data.get('gateway', {}).get('bind', 'loopback')
if bind == 'loopback':
    data['gateway']['auth'] = {'mode': 'none'}
else:
    # 非本地模式，保持 token 认证
    if data['gateway']['auth'].get('token', '').startswith('__'):
        data['gateway']['auth']['token'] = secrets.token_hex(24)
```

---

## 六、API Key 自动验证流程

```python
def validate_and_configure(api_key):
    """一个 Key 搞定一切"""
    
    # 1. 检测 Key 类型
    if api_key.startswith('sk-sp-'):
        provider = 'bailian'
        base_url = 'https://coding.dashscope.aliyuncs.com/v1'
        key_type = 'Coding Plan'
    elif api_key.startswith('sk-') and len(api_key) > 50:
        provider = 'deepseek'
        base_url = 'https://api.deepseek.com/v1'
        key_type = 'DeepSeek'
    elif api_key.startswith('sk-'):
        provider = 'bailian'
        base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
        key_type = '百炼标准'
    else:
        return None, "无法识别的 Key 格式"
    
    # 2. 验证 Key（发一个 models 请求）
    test_url = f"{base_url}/models" if provider == 'deepseek' else f"{base_url}/chat/completions"
    # ... curl 验证 ...
    
    # 3. 返回配置
    return {
        'provider': provider,
        'base_url': base_url,
        'key_type': key_type,
        'models': detected_models
    }, None
```

---

## 七、实施优先级

### 阶段 1：消除令牌问题（30 分钟）

1. `openclaw.json.template`: `auth.mode` 改为 `"none"`
2. `restore-config.py`: `bind=loopback` 时强制 `auth.mode='none'`
3. `xyvaclaw-setup.sh`: 删除令牌显示代码

**效果**：用户安装后打开浏览器直接看到对话界面。

### 阶段 2：安装流程直线化（2 小时）

1. `xyvaclaw-setup.sh` 重构：
   - 4 步取代 8 步
   - 去掉所有 y/n 确认
   - 加入 API Key 交互式提问 + 自动验证
   - 自动安装 Node.js（brew 或 nvm）
   - 默认启动 gateway + 打开浏览器

**效果**：用户只需输入 API Key，其他全自动。

### 阶段 3：飞书独立配置（1 小时）

1. 新增 `xyvaclaw setup feishu` 子命令
2. 新增 `docs/FEISHU-SETUP.md` 教程

**效果**：飞书配置从安装流程中解耦，按需使用。

---

## 八、一句话总结

> **当前问题**：安装完了还要找令牌、抄令牌、贴令牌。  
> **解决方案**：本机模式关闭认证 + 安装流程直线化 = 用户只需粘贴一个 API Key。
