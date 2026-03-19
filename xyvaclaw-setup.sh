#!/bin/bash
# ============================================
# xyvaClaw 一键安装脚本 (macOS)
# 基于 OpenClaw 运行时的品牌化 AI 助手平台
#
# Usage:
#   bash xyvaclaw-setup.sh              # 交互式安装
#   bash xyvaclaw-setup.sh --auto       # 无人值守安装（自动应答所有提示）
#   DEEPSEEK_API_KEY=sk-xxx bash xyvaclaw-setup.sh --auto  # 全自动安装+配置
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
XYVACLAW_HOME="${XYVACLAW_HOME:-$HOME/.xyvaclaw}"
WIZARD_PORT=19090
BRAND="xyvaClaw"

# Auto mode: --auto or -y or AUTO_INSTALL=1
AUTO_MODE=false
for arg in "$@"; do
    case "$arg" in
        --auto|-y|--yes) AUTO_MODE=true ;;
    esac
done
[ "${AUTO_INSTALL:-}" = "1" ] && AUTO_MODE=true

auto_confirm() {
    # In auto mode, return the default answer; otherwise read from user
    local prompt="$1" default="${2:-y}"
    if [ "$AUTO_MODE" = true ]; then
        REPLY="$default"
        echo -e "$prompt $default (auto)"
        return 0
    fi
    read -p "$prompt" -n 1 -r
    echo ""
}

auto_confirm_line() {
    local prompt="$1" default="${2:-}"
    if [ "$AUTO_MODE" = true ]; then
        REPLY="$default"
        echo -e "$prompt (auto)"
        return 0
    fi
    read -p "$prompt" -r
}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}${BOLD}"
    echo "  ██╗  ██╗██╗   ██╗██╗   ██╗ █████╗  ██████╗██╗      █████╗ ██╗    ██╗"
    echo "  ╚██╗██╔╝╚██╗ ██╔╝██║   ██║██╔══██╗██╔════╝██║     ██╔══██╗██║    ██║"
    echo "   ╚███╔╝  ╚████╔╝ ██║   ██║███████║██║     ██║     ███████║██║ █╗ ██║"
    echo "   ██╔██╗   ╚██╔╝  ╚██╗ ██╔╝██╔══██║██║     ██║     ██╔══██║██║███╗██║"
    echo "  ██╔╝ ██╗   ██║    ╚████╔╝ ██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝"
    echo "  ╚═╝  ╚═╝   ╚═╝     ╚═══╝  ╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝"
    echo -e "${NC}"
    echo -e "  ${BOLD}Your AI Assistant Platform${NC}"
    echo -e "  ${BLUE}Powered by OpenClaw Runtime${NC}"
    echo ""
}

log_step() {
    echo -e "\n${GREEN}${BOLD}[$1]${NC} $2"
}

log_ok() {
    echo -e "  ${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "  ${YELLOW}⚠️${NC}  $1"
}

log_fail() {
    echo -e "  ${RED}❌${NC} $1"
}

log_info() {
    echo -e "  ${BLUE}ℹ${NC}  $1"
}

banner

# ============================================
# Step 1: Check system dependencies
# ============================================
log_step "1/8" "检查系统环境..."

MISSING=()

# Node.js
if command -v node &>/dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
        MISSING+=("node (当前 $NODE_VER, 需要 22+)")
    else
        log_ok "Node.js $NODE_VER"
    fi
else
    MISSING+=("node")
fi

# Python 3
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    log_ok "Python $PY_VER"
else
    MISSING+=("python3")
fi

# ffmpeg
if command -v ffmpeg &>/dev/null; then
    log_ok "ffmpeg"
else
    MISSING+=("ffmpeg")
fi

# Homebrew
if command -v brew &>/dev/null; then
    log_ok "Homebrew"
else
    MISSING+=("homebrew")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    log_warn "缺少以下依赖:"
    for dep in "${MISSING[@]}"; do
        echo "   - $dep"
    done
    echo ""
    auto_confirm "是否自动安装？(y/n) " y
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if ! command -v brew &>/dev/null; then
            echo "📦 安装 Homebrew..."
            echo ""
            echo "  如果下载很慢，可以按 Ctrl+C 取消，然后使用国内镜像安装："
            echo "  /bin/zsh -c \"\$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/Homebrew.sh)\""
            echo ""
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        for dep in "${MISSING[@]}"; do
            case "$dep" in
                node*) brew install node ;;
                python3) brew install python ;;
                ffmpeg) brew install ffmpeg ;;
            esac
        done
    else
        log_fail "请先安装缺失依赖后重试"
        exit 1
    fi
fi

# ============================================
# Step 1.5: Detect existing Claw installations
# ============================================
# Detect and auto-clean existing Claw installations to avoid conflicts.
cleanup_existing_claws() {
    set +eo pipefail
    local FOUND_ISSUES=false

    # --- Stop and remove ALL OpenClaw/xyvaClaw launchd services (macOS) ---
    if [ "$(uname)" = "Darwin" ]; then
        for svc_label in "ai.openclaw.gateway" "ai.xyvaclaw.gateway"; do
            local SVC_MATCH
            SVC_MATCH=$(launchctl list 2>/dev/null | grep "$svc_label" 2>/dev/null || true)
            if [ -n "$SVC_MATCH" ]; then
                FOUND_ISSUES=true
                log_info "检测到已有服务 $svc_label，正在停止..."
                launchctl bootout gui/$(id -u)/$svc_label 2>/dev/null || true
                log_ok "服务 $svc_label 已停止"
            fi
        done
        # Remove all related plist files
        for plist in "$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist" \
                     "$HOME/Library/LaunchAgents/ai.xyvaclaw.gateway.plist"; do
            if [ -f "$plist" ]; then
                rm -f "$plist" 2>/dev/null || true
            fi
        done
    fi

    # --- Remove existing OpenClaw config directory (~/.openclaw) ---
    local OPENCLAW_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
    if [ -d "$OPENCLAW_DIR" ] && [ "$OPENCLAW_DIR" != "$XYVACLAW_HOME" ]; then
        FOUND_ISSUES=true
        log_info "检测到原版 OpenClaw 配置目录: $OPENCLAW_DIR"
        if [ "$AUTO_MODE" = true ]; then
            rm -rf "$OPENCLAW_DIR"
            log_ok "原版 OpenClaw 配置已清理"
        else
            echo ""
            echo -e "  ${BOLD}xyvaClaw 使用独立目录 ${XYVACLAW_HOME}${NC}"
            echo -e "  原版 OpenClaw 配置目录: ${OPENCLAW_DIR}"
            echo ""
            read -p "  是否删除原版 OpenClaw 配置？(y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$OPENCLAW_DIR"
                log_ok "原版 OpenClaw 配置已清理"
            else
                log_info "保留原版配置，继续安装"
            fi
        fi
    fi

    # --- Remove previous xyvaClaw installation (~/.xyvaclaw) ---
    if [ -d "$XYVACLAW_HOME" ]; then
        FOUND_ISSUES=true
        log_info "检测到已有 xyvaClaw 安装: $XYVACLAW_HOME"
        if [ "$AUTO_MODE" = true ]; then
            rm -rf "$XYVACLAW_HOME"
            log_ok "旧版 xyvaClaw 已清理"
        else
            echo ""
            read -p "  是否删除旧版 xyvaClaw 并全新安装？(y=全新安装 / n=保留合并) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$XYVACLAW_HOME"
                log_ok "旧版 xyvaClaw 已清理"
            else
                log_info "保留现有数据，合并安装"
            fi
        fi
    fi

    # --- Detect and remove other Claw desktop apps (macOS) ---
    local OTHER_CLAWS=()
    for app_name in "QClaw" "AutoClaw" "WorkBuddy" "CoPaw" "OpenClaw" "MoltBot" "ClawdBot"; do
        if [ -d "/Applications/${app_name}.app" ]; then
            OTHER_CLAWS+=("/Applications/${app_name}.app")
        elif [ -d "$HOME/Applications/${app_name}.app" ]; then
            OTHER_CLAWS+=("$HOME/Applications/${app_name}.app")
        fi
    done
    if [ ${#OTHER_CLAWS[@]} -gt 0 ]; then
        FOUND_ISSUES=true
        log_info "检测到其他 Claw 产品: ${OTHER_CLAWS[*]}"
        for app_path in "${OTHER_CLAWS[@]}"; do
            local app_base
            app_base=$(basename "$app_path")
            # Kill running processes
            pkill -f "$app_base" 2>/dev/null || true
            if [ "$AUTO_MODE" = true ]; then
                rm -rf "$app_path"
                log_ok "已删除: $app_base"
            else
                read -p "  是否删除 ${app_base}？(y/n) " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    rm -rf "$app_path"
                    log_ok "已删除: $app_base"
                fi
            fi
        done
    fi

    # --- Kill processes on port 18789 ---
    if command -v lsof &>/dev/null; then
        local PORT_PIDS
        PORT_PIDS=$(lsof -ti:18789 2>/dev/null || true)
        if [ -n "$PORT_PIDS" ]; then
            FOUND_ISSUES=true
            log_info "端口 18789 被占用，正在释放..."
            echo "$PORT_PIDS" | xargs kill -9 2>/dev/null || true
            sleep 1
            log_ok "端口 18789 已释放"
        fi
    fi

    if [ "$FOUND_ISSUES" = true ]; then
        echo ""
        log_ok "环境清理完成，开始全新安装 xyvaClaw"
        echo ""
    fi
    set -eo pipefail
}

# Run cleanup (do NOT suppress output — user needs to see what's being cleaned)
cleanup_existing_claws || true

# ============================================
# Step 2: Install OpenClaw runtime
# ============================================
log_step "2/8" "安装 OpenClaw 运行时..."

if command -v openclaw &>/dev/null; then
    CURRENT_VER=$(openclaw --version 2>/dev/null || echo "unknown")
    log_ok "OpenClaw 已安装 ($CURRENT_VER)"
else
    log_info "安装 OpenClaw..."
    npm install -g openclaw@latest
    log_ok "OpenClaw 安装完成"
fi

# ============================================
# Step 3: Create xyvaClaw home directory
# ============================================
log_step "3/8" "创建 $BRAND 数据目录..."

if [ -d "$XYVACLAW_HOME" ]; then
    log_info "$XYVACLAW_HOME 已存在，将合并部署新文件"
else
    mkdir -p "$XYVACLAW_HOME"
fi

# Deploy config-base
log_info "部署配置文件..."
for dir in agents workspace extensions config completions scripts; do
    if [ -d "$SCRIPT_DIR/config-base/$dir" ]; then
        rsync -a --ignore-existing "$SCRIPT_DIR/config-base/$dir/" "$XYVACLAW_HOME/$dir/"
        log_ok "$dir/"
    fi
done

# Copy openclaw.json template
if [ -f "$SCRIPT_DIR/config-base/openclaw.json.template" ]; then
    cp "$SCRIPT_DIR/config-base/openclaw.json.template" "$XYVACLAW_HOME/openclaw.json.template"
    log_ok "openclaw.json.template"
fi

# Clean up __API_KEY__ placeholders in agent configs
# Agent-level models.json with __API_KEY__ would override real keys from openclaw.json
PLACEHOLDER_FILES=$(grep -rl '"__API_KEY__"\|"__APP_ID__"\|"__APP_SECRET__"' "$XYVACLAW_HOME/agents" 2>/dev/null || true)
if [ -n "$PLACEHOLDER_FILES" ]; then
    log_info "清理 agent 配置中的占位符..."
    for pf in $PLACEHOLDER_FILES; do
        python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as f: d = json.load(f)
changed = False
def clean(obj):
    global changed
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if isinstance(obj[k], str) and obj[k].startswith('__') and obj[k].endswith('__'):
                del obj[k]
                changed = True
            else:
                clean(obj[k])
    elif isinstance(obj, list):
        for item in obj:
            clean(item)
clean(d)
if changed:
    with open(p, 'w') as f: json.dump(d, f, indent=2, ensure_ascii=False)
    print(f'  cleaned: {p}')
" "$pf"
    done
    log_ok "占位符已清理"
fi

# Create runtime directories
mkdir -p "$XYVACLAW_HOME"/{workspace/memory,workspace/output/{audio,video,temp},workspace/.reasoning,workspace/state,logs,memory,sessions,cache,secrets,identity,cron,delivery-queue}
log_ok "运行时目录"

# ============================================
# Step 4: Configure API Key
# ============================================
log_step "4/8" "配置 $BRAND..."

ENV_FILE="$XYVACLAW_HOME/.env"
if [ ! -f "$ENV_FILE" ]; then
    cp "$SCRIPT_DIR/templates/.env.template" "$ENV_FILE"
fi

# Collect API Key — from environment variable or interactive prompt
API_KEY=""

# Priority 1: environment variables already set
if [ -n "${BAILIAN_API_KEY:-}" ]; then
    API_KEY="$BAILIAN_API_KEY"
elif [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    API_KEY="$DEEPSEEK_API_KEY"
fi

# Priority 2: already configured in .env
if [ -z "$API_KEY" ] && [ -f "$ENV_FILE" ]; then
    API_KEY=$(grep -m1 '^BAILIAN_API_KEY=.\+' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
    [ -z "$API_KEY" ] && API_KEY=$(grep -m1 '^DEEPSEEK_API_KEY=.\+' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)
fi

# Priority 3: interactive prompt (skip in auto mode)
if [ -z "$API_KEY" ] && [ "$AUTO_MODE" != true ]; then
    echo ""
    echo -e "  ${BOLD}请粘贴你的 API Key${NC}"
    echo ""
    echo -e "  获取方式（任选其一）:"
    echo -e "    ${CYAN}百炼${NC}: https://bailian.console.aliyun.com → API-KEY 管理 → 创建"
    echo -e "    ${CYAN}DeepSeek${NC}: https://platform.deepseek.com/api_keys"
    echo ""
    read -p "  API Key: " -r API_KEY
    echo ""
fi

# Detect key type and write to .env
if [ -n "$API_KEY" ]; then
    KEY_TYPE=""
    KEY_VAR=""
    if echo "$API_KEY" | grep -q '^sk-sp-'; then
        KEY_TYPE="百炼 Coding Plan"
        KEY_VAR="BAILIAN_API_KEY"
    elif echo "$API_KEY" | grep -q '^sk-' && [ ${#API_KEY} -gt 50 ]; then
        KEY_TYPE="DeepSeek"
        KEY_VAR="DEEPSEEK_API_KEY"
    elif echo "$API_KEY" | grep -q '^sk-'; then
        KEY_TYPE="百炼标准"
        KEY_VAR="BAILIAN_API_KEY"
    else
        KEY_TYPE="自定义"
        KEY_VAR="BAILIAN_API_KEY"
    fi

    # Write to .env (use python to avoid sed special char issues)
    python3 -c "
import sys
key_var, key_val = sys.argv[1], sys.argv[2]
env_path = sys.argv[3]
lines = []
found = False
with open(env_path) as f:
    for line in f:
        if line.startswith(key_var + '='):
            lines.append(key_var + '=' + key_val + '\n')
            found = True
        else:
            lines.append(line)
if not found:
    lines.append(key_var + '=' + key_val + '\n')
with open(env_path, 'w') as f:
    f.writelines(lines)
" "$KEY_VAR" "$API_KEY" "$ENV_FILE"

    # Also write feishu vars from environment if present
    [ -n "${FEISHU_APP_ID:-}" ] && python3 -c "
import sys; v,k,p=sys.argv[1],sys.argv[2],sys.argv[3]
lines=[]; found=False
with open(p) as f:
    for l in f:
        if l.startswith(v+'='): lines.append(v+'='+k+'\n'); found=True
        else: lines.append(l)
if not found: lines.append(v+'='+k+'\n')
with open(p,'w') as f: f.writelines(lines)
" "FEISHU_APP_ID" "$FEISHU_APP_ID" "$ENV_FILE"

    [ -n "${FEISHU_APP_SECRET:-}" ] && python3 -c "
import sys; v,k,p=sys.argv[1],sys.argv[2],sys.argv[3]
lines=[]; found=False
with open(p) as f:
    for l in f:
        if l.startswith(v+'='): lines.append(v+'='+k+'\n'); found=True
        else: lines.append(l)
if not found: lines.append(v+'='+k+'\n')
with open(p,'w') as f: f.writelines(lines)
" "FEISHU_APP_SECRET" "$FEISHU_APP_SECRET" "$ENV_FILE"

    log_ok "$KEY_TYPE 密钥已写入"

    # Validate key (quick test)
    log_info "验证 API Key..."
    VALIDATE_OK=false
    if [ "$KEY_VAR" = "BAILIAN_API_KEY" ]; then
        if echo "$API_KEY" | grep -q '^sk-sp-'; then
            TEST_URL="https://coding.dashscope.aliyuncs.com/v1/chat/completions"
        else
            TEST_URL="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        fi
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "$TEST_URL" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            VALIDATE_OK=true
        fi
    elif [ "$KEY_VAR" = "DEEPSEEK_API_KEY" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 10 "https://api.deepseek.com/v1/chat/completions" \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' 2>/dev/null || echo "000")
        if [ "$HTTP_CODE" = "200" ]; then
            VALIDATE_OK=true
        fi
    fi

    if [ "$VALIDATE_OK" = true ]; then
        log_ok "API Key 验证通过"
    else
        log_warn "API Key 验证未通过（HTTP $HTTP_CODE），请确认 Key 是否正确。安装将继续。"
    fi
else
    log_warn "未配置 API Key，安装后请编辑 $ENV_FILE"
fi

# Generate config from .env + template
if [ -f "$XYVACLAW_HOME/openclaw.json.template" ]; then
    log_info "生成配置文件..."
    cd "$XYVACLAW_HOME"
    python3 "$SCRIPT_DIR/installer/restore-config.py" \
        "$XYVACLAW_HOME/openclaw.json.template" \
        "$ENV_FILE"
    log_ok ".openclaw/openclaw.json 已生成"
fi

# ============================================
# Step 4.5: Register local plugins with OpenClaw
# ============================================
OPENCLAW_CONFIG="$XYVACLAW_HOME/.openclaw/openclaw.json"
if [ -f "$OPENCLAW_CONFIG" ]; then
    log_info "注册本地插件到 OpenClaw..."

    # Save plugins AND channels config, then temporarily strip both.
    # OpenClaw validates the ENTIRE config before running any command, so:
    #   - unknown channel IDs (e.g. "webchat") → config invalid → plugins install fails
    #   - unregistered plugin names in plugins.allow → config invalid → plugins install fails
    # We must produce a minimal valid config so `openclaw plugins install --link` can run.
    python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as f: d = json.load(f)
stash = {
    'plugins': d.get('plugins', {}),
    'channels': d.get('channels', {}),
}
with open(p + '.stash', 'w') as f: json.dump(stash, f)
d['plugins'] = {'allow': [], 'slots': {}, 'entries': {}}
d['channels'] = {}
with open(p, 'w') as f: json.dump(d, f, indent=2)
" "$OPENCLAW_CONFIG"

    export OPENCLAW_HOME="$XYVACLAW_HOME"

    # Register lossless-claw
    PLUGINS_OK=true
    if [ -d "$XYVACLAW_HOME/extensions/lossless-claw" ]; then
        if openclaw plugins install --link "$XYVACLAW_HOME/extensions/lossless-claw" 2>&1 | tail -3; then
            log_ok "lossless-claw 插件已注册"
        else
            log_warn "lossless-claw 插件注册失败（将使用手动注入）"
            PLUGINS_OK=false
        fi
    fi

    # Register feishu_local
    if [ -d "$XYVACLAW_HOME/extensions/feishu" ]; then
        if openclaw plugins install --link "$XYVACLAW_HOME/extensions/feishu" 2>&1 | tail -3; then
            log_ok "feishu_local 插件已注册"
        else
            log_warn "feishu_local 插件注册失败（将使用手动注入）"
            PLUGINS_OK=false
        fi
    fi

    # Fallback: if openclaw plugins install failed, manually inject load.paths
    if [ "$PLUGINS_OK" = false ]; then
        log_info "手动注入插件路径..."
        python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as f: d = json.load(f)
load = d.setdefault('plugins', {}).setdefault('load', {})
paths = load.get('paths', [])
for ext_path in ['\$OPENCLAW_HOME/extensions/lossless-claw', '\$OPENCLAW_HOME/extensions/feishu']:
    if ext_path not in paths:
        paths.append(ext_path)
load['paths'] = paths
d['plugins']['load'] = load
with open(p, 'w') as f: json.dump(d, f, indent=2)
print('injected load.paths:', paths)
" "$OPENCLAW_CONFIG"
    fi

    # Merge stashed plugins + channels back into the config that openclaw
    # plugins install wrote (preserving load.paths and installs registry).
    # Also filter out unknown channel IDs to prevent config validation errors.
    python3 -c "
import json, sys, os
p = sys.argv[1]
stash_path = p + '.stash'
if not os.path.exists(stash_path):
    sys.exit(0)
with open(p) as f: d = json.load(f)
with open(stash_path) as f: stash = json.load(f)

# --- Restore plugins (merge) ---
saved_plugins = stash.get('plugins', {})
cur = d.setdefault('plugins', {})
cur_allow = cur.get('allow', [])
for item in saved_plugins.get('allow', []):
    if item not in cur_allow:
        cur_allow.append(item)
cur['allow'] = cur_allow
cur.setdefault('slots', {}).update(saved_plugins.get('slots', {}))
cur_entries = cur.setdefault('entries', {})
for name, entry in saved_plugins.get('entries', {}).items():
    if name not in cur_entries:
        cur_entries[name] = entry
    else:
        if 'config' in entry:
            cur_entries[name].setdefault('config', {}).update(entry['config'])
        if 'enabled' in entry:
            cur_entries[name]['enabled'] = entry['enabled']
d['plugins'] = cur

# --- Restore channels (filter out unknown IDs) ---
KNOWN_CHANNELS = {'feishu', 'dingtalk', 'slack', 'discord', 'telegram', 'wechat', 'whatsapp', 'webchat'}
saved_channels = stash.get('channels', {})
for ch_name, ch_conf in saved_channels.items():
    if ch_name in KNOWN_CHANNELS:
        d.setdefault('channels', {})[ch_name] = ch_conf

with open(p, 'w') as f: json.dump(d, f, indent=2)
os.remove(stash_path)
" "$OPENCLAW_CONFIG"

    log_ok "插件配置已恢复"
fi

# ============================================
# Step 5: Generate identity files from templates
# ============================================
log_step "5/8" "生成身份文件..."

# SOUL.md (universal)
if [ ! -f "$XYVACLAW_HOME/workspace/SOUL.md" ]; then
    if [ -f "$SCRIPT_DIR/templates/SOUL.md.template" ]; then
        cp "$SCRIPT_DIR/templates/SOUL.md.template" "$XYVACLAW_HOME/workspace/SOUL.md"
    fi
    log_ok "SOUL.md"
fi

# IDENTITY.md
ASSISTANT_NAME="${ASSISTANT_NAME:-AI Assistant}"
if [ -f "$XYVACLAW_HOME/.env" ]; then
    ENV_NAME=$(grep '^ASSISTANT_NAME=' "$XYVACLAW_HOME/.env" 2>/dev/null | cut -d= -f2-)
    if [ -n "$ENV_NAME" ]; then
        ASSISTANT_NAME="$ENV_NAME"
    fi
fi

if [ ! -f "$XYVACLAW_HOME/workspace/IDENTITY.md" ]; then
    cat > "$XYVACLAW_HOME/workspace/IDENTITY.md" << IDENTITY_EOF
# IDENTITY.md - Who I Am

- **Name:** ${ASSISTANT_NAME}
- **Platform:** xyvaClaw
- **Vibe:** Helpful, direct, and resourceful

---

Your AI assistant, ready to help.
IDENTITY_EOF
    log_ok "IDENTITY.md (name: $ASSISTANT_NAME)"
fi

# AGENTS.md
if [ ! -f "$XYVACLAW_HOME/workspace/AGENTS.md" ]; then
    if [ -f "$SCRIPT_DIR/templates/AGENTS.md.template" ]; then
        cp "$SCRIPT_DIR/templates/AGENTS.md.template" "$XYVACLAW_HOME/workspace/AGENTS.md"
    fi
    log_ok "AGENTS.md"
fi

# MEMORY.md
if [ ! -f "$XYVACLAW_HOME/workspace/MEMORY.md" ]; then
    echo "# MEMORY.md" > "$XYVACLAW_HOME/workspace/MEMORY.md"
    echo "" >> "$XYVACLAW_HOME/workspace/MEMORY.md"
    echo "No memories yet. Start chatting to build up context." >> "$XYVACLAW_HOME/workspace/MEMORY.md"
    log_ok "MEMORY.md"
fi

# USER.md
if [ ! -f "$XYVACLAW_HOME/workspace/USER.md" ]; then
    echo "# USER.md - About You" > "$XYVACLAW_HOME/workspace/USER.md"
    echo "" >> "$XYVACLAW_HOME/workspace/USER.md"
    echo "Tell your assistant about yourself here." >> "$XYVACLAW_HOME/workspace/USER.md"
    log_ok "USER.md"
fi

# SESSION-STATE.md
if [ ! -f "$XYVACLAW_HOME/workspace/SESSION-STATE.md" ]; then
    echo "# Session State" > "$XYVACLAW_HOME/workspace/SESSION-STATE.md"
    echo "" >> "$XYVACLAW_HOME/workspace/SESSION-STATE.md"
    echo "No active sessions." >> "$XYVACLAW_HOME/workspace/SESSION-STATE.md"
    log_ok "SESSION-STATE.md"
fi

# ============================================
# Step 6: Install dependencies
# ============================================
log_step "6/8" "安装依赖..."

# Feishu extension npm deps
if [ -d "$XYVACLAW_HOME/extensions/feishu" ] && [ -f "$XYVACLAW_HOME/extensions/feishu/package.json" ]; then
    log_info "安装飞书扩展依赖..."
    (cd "$XYVACLAW_HOME/extensions/feishu" && npm install --production 2>/dev/null) && log_ok "feishu extension" || log_warn "feishu extension npm install 失败（启动后会自动安装）"
fi

# Lossless-claw extension
if [ -d "$XYVACLAW_HOME/extensions/lossless-claw" ] && [ -f "$XYVACLAW_HOME/extensions/lossless-claw/package.json" ]; then
    log_info "安装 lossless-claw 依赖..."
    (cd "$XYVACLAW_HOME/extensions/lossless-claw" && npm install --production 2>/dev/null) && log_ok "lossless-claw" || log_warn "lossless-claw npm install 失败"
fi

# Skills with package.json
SKILL_COUNT=0
for pkg_json in "$XYVACLAW_HOME/workspace/skills"/*/package.json; do
    if [ -f "$pkg_json" ]; then
        skill_dir=$(dirname "$pkg_json")
        skill_name=$(basename "$skill_dir")
        (cd "$skill_dir" && npm install --production 2>/dev/null) && SKILL_COUNT=$((SKILL_COUNT + 1)) || true
    fi
done
if [ $SKILL_COUNT -gt 0 ]; then
    log_ok "$SKILL_COUNT 个技能的 npm 依赖"
fi

# Python deps
pip3 install --user edge-tts 2>/dev/null && log_ok "edge-tts (Python)" || log_warn "edge-tts 安装失败"
pip3 install --user python-pptx 2>/dev/null && log_ok "python-pptx (Python)" || log_warn "python-pptx 安装失败（PPT 生成功能不可用）"
pip3 install --user pdfplumber PyPDF2 2>/dev/null && log_ok "pdfplumber + PyPDF2 (Python)" || log_warn "PDF 库安装失败（PDF 处理功能不可用）"

# ============================================
# Step 7: Configure environment + startup
# ============================================
log_step "7/8" "配置环境..."

# Write OPENCLAW_HOME to shell profile
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_RC="$HOME/.bash_profile"
fi

if [ -n "$SHELL_RC" ]; then
    if ! grep -q "OPENCLAW_HOME" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# xyvaClaw - AI Assistant Platform" >> "$SHELL_RC"
        echo "export OPENCLAW_HOME=\"\$HOME/.xyvaclaw\"" >> "$SHELL_RC"
        log_ok "已添加 OPENCLAW_HOME 到 $SHELL_RC"
    else
        log_ok "OPENCLAW_HOME 已存在于 $SHELL_RC"
    fi
fi

# Create xyvaclaw wrapper
WRAPPER_PATH="/usr/local/bin/xyvaclaw"
if [ ! -f "$WRAPPER_PATH" ] || [ ! -x "$WRAPPER_PATH" ]; then
    sudo tee "$WRAPPER_PATH" > /dev/null << 'WRAPPER_EOF'
#!/bin/bash
export OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.xyvaclaw}"
exec openclaw "$@"
WRAPPER_EOF
    sudo chmod +x "$WRAPPER_PATH"
    log_ok "xyvaclaw 命令已创建"
fi

# Feishu secret to secrets dir
if [ -f "$XYVACLAW_HOME/.env" ]; then
    FEISHU_SECRET=$(grep '^FEISHU_APP_SECRET=' "$XYVACLAW_HOME/.env" 2>/dev/null | cut -d= -f2-)
    if [ -n "$FEISHU_SECRET" ]; then
        echo "FEISHU_APP_SECRET=$FEISHU_SECRET" > "$XYVACLAW_HOME/secrets/feishu.env"
        chmod 600 "$XYVACLAW_HOME/secrets/feishu.env"
        log_ok "feishu.env (chmod 600)"
    fi
fi

# LaunchAgent (auto-start) — always configure
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/ai.xyvaclaw.gateway.plist"

if [ ! -f "$PLIST_FILE" ]; then
    mkdir -p "$PLIST_DIR"
    OPENCLAW_BIN=$(which openclaw 2>/dev/null || echo "/usr/local/bin/openclaw")
    cat > "$PLIST_FILE" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.xyvaclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>${OPENCLAW_BIN}</string>
        <string>gateway</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>OPENCLAW_HOME</key>
        <string>${XYVACLAW_HOME}</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${XYVACLAW_HOME}/logs/gateway.log</string>
    <key>StandardErrorPath</key>
    <string>${XYVACLAW_HOME}/logs/gateway.err.log</string>
</dict>
</plist>
PLIST_EOF
    log_ok "LaunchAgent 已创建"
fi

# ============================================
# Post-install: check for updates (anonymous)
# ============================================
INSTALL_MODE="interactive"
[ "$AUTO_MODE" = true ] && INSTALL_MODE="auto"
(curl -sS -m 5 -X POST "https://api.xyvaclaw.com/v1/setup-complete" \
  -H "Content-Type: application/json" \
  -d "{\"os\":\"macos\",\"v\":\"1.1.5\",\"mode\":\"${INSTALL_MODE}\"}" \
  2>/dev/null || true) &

# ============================================
# Done!
# ============================================
echo ""
echo -e "${GREEN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}  🎉 $BRAND 安装完成！${NC}"
echo -e "${GREEN}${BOLD}============================================${NC}"
echo ""
echo -e "  ${BOLD}数据目录:${NC} $XYVACLAW_HOME"
echo ""
echo -e "  ${CYAN}${BOLD}▶ 如何使用（3 步）:${NC}"
echo ""
echo -e "  ${BOLD}1. 启动:${NC}"
echo "     xyvaclaw gateway"
echo ""
echo -e "  ${BOLD}2. 打开浏览器访问:${NC}"
echo "     http://localhost:18789"
echo ""
echo -e "  ${BOLD}3. 开始和你的 AI 助手对话！${NC}"
echo ""
echo -e "  ${BOLD}常用命令:${NC}"
echo "    xyvaclaw gateway          # 启动 AI 助手"
echo "    xyvaclaw gateway status   # 查看运行状态"
echo "    xyvaclaw agents list      # 查看 agent 列表"
echo ""
echo -e "  ${BOLD}首次启动注意:${NC}"
echo "    - 会下载本地 embedding 模型（约 70MB），请耐心等待约 1 分钟"
echo ""
echo -e "  ${BOLD}飞书机器人配置（必须在飞书开放平台完成）:${NC}"
echo "    1. open.feishu.cn → 你的应用 → 事件与回调"
echo "    2. 订阅方式：选择「使用长连接接收事件」(WebSocket)"
echo "    3. 添加事件：im.message.receive_v1（接收消息）"
echo "    4. 权限管理：开通「获取与发送单聊/群组消息」"
echo "    5. 版本管理与发布 → 创建版本并发布上线"
echo "    6. 将机器人拉入群 → @机器人名字 即可对话"
echo ""
echo -e "  ${BOLD}遇到问题？${NC}"
echo "    - 常见问题: https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FAQ.md"
echo "    - QQ 群: 1087471835"
echo "    - Discord: https://discord.gg/QABg4Z2Mzu"
echo ""

# Auto-start gateway
echo ""
log_info "启动 gateway..."
{
    export OPENCLAW_HOME="$XYVACLAW_HOME"

    # Always start gateway in background so the script can finish cleanly
    nohup openclaw gateway > "$XYVACLAW_HOME/logs/gateway.log" 2>&1 &
    GATEWAY_PID=$!
    sleep 3

    # Verify gateway is actually running
    if kill -0 $GATEWAY_PID 2>/dev/null; then
        log_ok "Gateway 已在后台启动 (PID: $GATEWAY_PID)"
        echo ""
        echo -e "  ${BOLD}Dashboard:${NC} http://localhost:18789"
        echo -e "  ${BOLD}查看日志:${NC} tail -f $XYVACLAW_HOME/logs/gateway.log"
        echo -e "  ${BOLD}停止服务:${NC} kill $GATEWAY_PID"
        echo ""

        # Open browser — no token needed (auth mode=none for loopback)
        if command -v open &>/dev/null; then
            log_info "正在打开浏览器..."
            open "http://localhost:18789" 2>/dev/null || true
        fi
    else
        log_warn "Gateway 启动可能失败，请检查日志: $XYVACLAW_HOME/logs/gateway.log"
    fi
}
