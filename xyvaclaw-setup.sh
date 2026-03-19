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

# Create runtime directories
mkdir -p "$XYVACLAW_HOME"/{workspace/memory,workspace/output/{audio,video,temp},workspace/.reasoning,workspace/state,logs,memory,sessions,cache,secrets,identity,cron,delivery-queue}
log_ok "运行时目录"

# ============================================
# Step 4: Setup wizard or manual config
# ============================================
log_step "4/8" "配置 $BRAND..."

WIZARD_DIR="$SCRIPT_DIR/setup-wizard"
USE_WIZARD=false

if [ -d "$WIZARD_DIR" ] && [ -f "$WIZARD_DIR/package.json" ]; then
    if [ "$AUTO_MODE" = true ]; then
        # Auto mode: skip wizard, use env vars or .env template directly
        log_info "无人值守模式：跳过 Web 向导，使用环境变量/模板配置"
        USE_WIZARD=false
    else
        echo ""
        echo -e "  ${BOLD}选择配置方式:${NC}"
        echo "    1) 🌐 Web 配置向导 (推荐，图形界面)"
        echo "    2) 📝 手动编辑 .env 文件"
        echo ""
        read -p "  请选择 (1/2): " -n 1 -r
        echo ""

        if [[ $REPLY == "1" ]]; then
            USE_WIZARD=true
        fi
    fi
fi

if [ "$USE_WIZARD" = true ]; then
    log_info "启动配置向导..."

    # Check if frontend is built (dist/ may be absent after git clone)
    NEED_BUILD=false
    if [ ! -f "$WIZARD_DIR/dist/index.html" ]; then
        NEED_BUILD=true
        log_info "前端未构建，正在安装依赖并构建..."
    elif [ -d "$WIZARD_DIR/src" ]; then
        # Rebuild if any source file is newer than the built output
        NEWEST_SRC=$(find "$WIZARD_DIR/src" -type f -newer "$WIZARD_DIR/dist/index.html" 2>/dev/null | head -1)
        if [ -n "$NEWEST_SRC" ]; then
            NEED_BUILD=true
            log_info "检测到前端源码更新，重新构建..."
        fi
    fi

    # Install wizard deps if needed
    if [ ! -d "$WIZARD_DIR/node_modules" ] || [ "$(ls -A "$WIZARD_DIR/node_modules" 2>/dev/null | head -1)" = "" ]; then
        log_info "安装配置向导依赖 (npm install)..."
        if [ "$NEED_BUILD" = true ]; then
            # Full install needed (includes vite for building)
            (cd "$WIZARD_DIR" && npm install) || {
                log_warn "npm install 失败，将使用手动配置"
                USE_WIZARD=false
            }
        else
            # Distribution mode: only server deps needed
            (cd "$WIZARD_DIR" && npm install --production) || {
                log_warn "npm install 失败，将使用手动配置"
                USE_WIZARD=false
            }
        fi
    fi

    # Build frontend if needed
    if [ "$USE_WIZARD" = true ] && [ "$NEED_BUILD" = true ]; then
        log_info "构建前端页面 (vite build)..."
        (cd "$WIZARD_DIR" && npx --yes vite build) || {
            log_warn "前端构建失败，将使用手动配置"
            USE_WIZARD=false
        }
        if [ "$USE_WIZARD" = true ] && [ -f "$WIZARD_DIR/dist/index.html" ]; then
            log_ok "前端构建完成"
        fi
    fi
fi

if [ "$USE_WIZARD" = true ]; then
    # Start wizard server
    WIZARD_CONFIG="$XYVACLAW_HOME/.wizard-config.json"
    export XYVACLAW_HOME
    export WIZARD_CONFIG
    export WIZARD_PORT

    node "$WIZARD_DIR/server/index.js" &
    WIZARD_PID=$!

    # Wait for server to start
    sleep 3

    # Verify wizard server is running
    if ! kill -0 $WIZARD_PID 2>/dev/null; then
        log_warn "配置向导服务启动失败，将使用手动配置"
        USE_WIZARD=false
    fi
fi

if [ "$USE_WIZARD" = true ]; then
    echo ""
    echo -e "  ${BOLD}${CYAN}════════════════════════════════════════${NC}"
    echo -e "  ${BOLD}${CYAN}  🌐 配置向导已启动!${NC}"
    echo -e "  ${BOLD}${CYAN}════════════════════════════════════════${NC}"
    echo ""
    echo -e "  请在浏览器中完成配置: ${BOLD}http://localhost:${WIZARD_PORT}${NC}"
    echo ""
    echo -e "  ${YELLOW}• 在浏览器中填写 API Key、选择模型、配置飞书等${NC}"
    echo -e "  ${YELLOW}• 点击“保存配置”后向导会自动关闭，安装继续${NC}"
    echo -e "  ${YELLOW}• 或按 Ctrl+C 跳过向导，稍后手动编辑 .env 文件${NC}"
    echo ""

    # Open browser
    if command -v open &>/dev/null; then
        open "http://localhost:${WIZARD_PORT}" 2>/dev/null || true
    fi

    # Wait for wizard to finish (it calls process.exit(0) after save)
    log_info "等待配置完成..."
    wait $WIZARD_PID 2>/dev/null || true

    # Apply wizard config
    if [ -f "$WIZARD_CONFIG" ]; then
        log_info "应用向导配置..."
        cd "$XYVACLAW_HOME"
        python3 "$SCRIPT_DIR/installer/restore-config.py" \
            "$XYVACLAW_HOME/openclaw.json.template" \
            "$XYVACLAW_HOME/.env" \
            "$WIZARD_CONFIG"
        log_ok "配置已生成 (.openclaw/openclaw.json)"
    fi
else
    # Manual .env config
    ENV_FILE="$XYVACLAW_HOME/.env"
    if [ ! -f "$ENV_FILE" ]; then
        cp "$SCRIPT_DIR/templates/.env.template" "$ENV_FILE"
        log_info "已创建配置模板: $ENV_FILE"
    fi

    echo ""
    echo -e "  ${BOLD}请编辑 $ENV_FILE 填写你的 API 密钥${NC}"
    echo ""
    echo "  必填（至少一个模型 Provider）:"
    echo "    DEEPSEEK_API_KEY=你的DeepSeek密钥"
    echo "    或 BAILIAN_API_KEY=你的百炼密钥"
    echo ""
    echo "  选填（飞书通道）:"
    echo "    FEISHU_APP_ID=你的飞书应用ID"
    echo "    FEISHU_APP_SECRET=你的飞书应用密钥"
    echo ""

    # In auto mode, write env vars from environment into .env if provided
    if [ "$AUTO_MODE" = true ]; then
        log_info "无人值守模式：从环境变量写入配置..."
        # Write any provided API keys from env into the .env file
        [ -n "${DEEPSEEK_API_KEY:-}" ] && sed -i.bak "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${BAILIAN_API_KEY:-}" ] && sed -i.bak "s/^BAILIAN_API_KEY=.*/BAILIAN_API_KEY=${BAILIAN_API_KEY}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${FEISHU_APP_ID:-}" ] && sed -i.bak "s/^FEISHU_APP_ID=.*/FEISHU_APP_ID=${FEISHU_APP_ID}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${FEISHU_APP_SECRET:-}" ] && sed -i.bak "s/^FEISHU_APP_SECRET=.*/FEISHU_APP_SECRET=${FEISHU_APP_SECRET}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${ASSISTANT_NAME:-}" ] && sed -i.bak "s/^ASSISTANT_NAME=.*/ASSISTANT_NAME=${ASSISTANT_NAME}/" "$ENV_FILE" 2>/dev/null || true
        rm -f "${ENV_FILE}.bak"
        # Check if at least one key is configured
        if grep -qE '^(DEEPSEEK_API_KEY|BAILIAN_API_KEY)=.+' "$ENV_FILE" 2>/dev/null; then
            log_ok "API Key 已从环境变量写入"
        else
            log_warn "未检测到 API Key 环境变量，安装后请手动编辑 $ENV_FILE"
        fi
    else
        # Try to open editor
        if command -v code &>/dev/null; then
            read -p "  是否用 VS Code 打开？(y/n) " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                code "$ENV_FILE"
            fi
        fi

        read -p "  填写完成后按回车继续..." -r
    fi

    # Generate config from .env
    if [ -f "$XYVACLAW_HOME/openclaw.json.template" ]; then
        log_info "生成配置文件..."
        cd "$XYVACLAW_HOME"
        python3 "$SCRIPT_DIR/installer/restore-config.py" \
            "$XYVACLAW_HOME/openclaw.json.template" \
            "$ENV_FILE"
        log_ok ".openclaw/openclaw.json 已生成"
    fi
fi

# ============================================
# Step 4.5: Register local plugins with OpenClaw
# ============================================
OPENCLAW_CONFIG="$XYVACLAW_HOME/.openclaw/openclaw.json"
if [ -f "$OPENCLAW_CONFIG" ]; then
    log_info "注册本地插件到 OpenClaw..."

    # Save plugins config and temporarily clear it (OpenClaw validates plugins.allow
    # against its registry, so we must register plugins before referencing them)
    python3 -c "
import json, sys
p = sys.argv[1]
with open(p) as f: d = json.load(f)
plugins_backup = d.get('plugins', {})
with open(p + '.plugins-stash', 'w') as f: json.dump(plugins_backup, f)
d['plugins'] = {'allow': [], 'slots': {}, 'entries': {}}
with open(p, 'w') as f: json.dump(d, f, indent=2)
" "$OPENCLAW_CONFIG" 2>/dev/null

    export OPENCLAW_HOME="$XYVACLAW_HOME"

    # Register lossless-claw
    if [ -d "$XYVACLAW_HOME/extensions/lossless-claw" ]; then
        openclaw plugins install --link "$XYVACLAW_HOME/extensions/lossless-claw" 2>/dev/null \
            && log_ok "lossless-claw 插件已注册" \
            || log_warn "lossless-claw 插件注册失败"
    fi

    # Register feishu_local
    if [ -d "$XYVACLAW_HOME/extensions/feishu" ]; then
        openclaw plugins install --link "$XYVACLAW_HOME/extensions/feishu" 2>/dev/null \
            && log_ok "feishu_local 插件已注册" \
            || log_warn "feishu_local 插件注册失败"
    fi

    # Merge stashed plugin settings into what openclaw plugins install wrote
    # (preserving load.paths and installs registry that openclaw created)
    python3 -c "
import json, sys, os
p = sys.argv[1]
stash = p + '.plugins-stash'
if not os.path.exists(stash):
    sys.exit(0)
with open(p) as f: d = json.load(f)
with open(stash) as f: saved = json.load(f)
cur = d.setdefault('plugins', {})
# Merge allow list (union, preserving order)
cur_allow = cur.get('allow', [])
for item in saved.get('allow', []):
    if item not in cur_allow:
        cur_allow.append(item)
cur['allow'] = cur_allow
# Merge slots
cur.setdefault('slots', {}).update(saved.get('slots', {}))
# Merge entries (deep: preserve openclaw's enabled, add our config)
cur_entries = cur.setdefault('entries', {})
for name, entry in saved.get('entries', {}).items():
    if name not in cur_entries:
        cur_entries[name] = entry
    else:
        # Merge config from stash into existing entry
        if 'config' in entry:
            cur_entries[name].setdefault('config', {}).update(entry['config'])
        if 'enabled' in entry:
            cur_entries[name]['enabled'] = entry['enabled']
d['plugins'] = cur
with open(p, 'w') as f: json.dump(d, f, indent=2)
os.remove(stash)
" "$OPENCLAW_CONFIG" 2>/dev/null

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
    echo ""
    log_info "创建 xyvaclaw 命令..."
    auto_confirm "  需要 sudo 权限写入 /usr/local/bin/xyvaclaw，继续？(y/n) " y
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo tee "$WRAPPER_PATH" > /dev/null << 'WRAPPER_EOF'
#!/bin/bash
export OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.xyvaclaw}"
exec openclaw "$@"
WRAPPER_EOF
        sudo chmod +x "$WRAPPER_PATH"
        log_ok "xyvaclaw 命令已创建"
    fi
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

# LaunchAgent (auto-start)
echo ""
auto_confirm "  是否配置开机自启动？(y/n) " y

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/ai.xyvaclaw.gateway.plist"

if [[ $REPLY =~ ^[Yy]$ ]]; then
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
  -d "{\"os\":\"macos\",\"v\":\"1.1.4\",\"mode\":\"${INSTALL_MODE}\"}" \
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
echo "    - 飞书集成需在开放平台配置 webhook 回调地址"
echo ""
echo -e "  ${BOLD}遇到问题？${NC}"
echo "    - 常见问题: https://github.com/xyva-yuangui/XyvaClaw/blob/main/docs/FAQ.md"
echo "    - QQ 群: 1087471835"
echo "    - Discord: https://discord.gg/QABg4Z2Mzu"
echo ""

# Ask to start now
auto_confirm "  是否现在启动 gateway？(y/n) " y
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    log_info "启动 gateway..."
    export OPENCLAW_HOME="$XYVACLAW_HOME"

    # Always start gateway in background so the script can finish cleanly
    nohup openclaw gateway > "$XYVACLAW_HOME/logs/gateway.log" 2>&1 &
    GATEWAY_PID=$!
    sleep 3

    # Verify gateway is actually running
    if kill -0 $GATEWAY_PID 2>/dev/null; then
        log_ok "Gateway 已在后台启动 (PID: $GATEWAY_PID)"
        echo ""
        echo -e "  ${BOLD}查看日志:${NC} tail -f $XYVACLAW_HOME/logs/gateway.log"
        echo -e "  ${BOLD}停止服务:${NC} kill $GATEWAY_PID"
        echo ""

        # Open browser for the user
        if [ "$AUTO_MODE" != true ] && command -v open &>/dev/null; then
            log_info "正在打开浏览器..."
            open "http://localhost:18789" 2>/dev/null || true
        fi
    else
        log_warn "Gateway 启动可能失败，请检查日志: $XYVACLAW_HOME/logs/gateway.log"
    fi
fi
