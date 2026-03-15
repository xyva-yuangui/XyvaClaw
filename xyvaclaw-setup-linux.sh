#!/bin/bash
# ============================================
# xyvaClaw 一键安装脚本 (Linux)
# 基于 OpenClaw 运行时的品牌化 AI 助手平台
#
# Usage:
#   bash xyvaclaw-setup-linux.sh              # 交互式安装
#   bash xyvaclaw-setup-linux.sh --auto       # 无人值守安装
#   DEEPSEEK_API_KEY=sk-xxx bash xyvaclaw-setup-linux.sh --auto  # 全自动
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
    local prompt="$1" default="${2:-y}"
    if [ "$AUTO_MODE" = true ]; then
        REPLY="$default"
        echo -e "$prompt $default (auto)"
        return 0
    fi
    read -p "$prompt" -n 1 -r
    echo ""
}

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

log_step() { echo -e "\n${GREEN}${BOLD}[$1]${NC} $2"; }
log_ok() { echo -e "  ${GREEN}OK${NC} $1"; }
log_warn() { echo -e "  ${YELLOW}WARN${NC} $1"; }
log_fail() { echo -e "  ${RED}FAIL${NC} $1"; }
log_info() { echo -e "  ${BLUE}INFO${NC} $1"; }

banner

# ============================================
# Step 1: Check system dependencies
# ============================================
log_step "1/7" "检查系统环境..."

MISSING=()

if command -v node &>/dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
        MISSING+=("nodejs (当前 $NODE_VER, 需要 22+)")
    else
        log_ok "Node.js $NODE_VER"
    fi
else
    MISSING+=("nodejs")
fi

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    log_ok "Python $PY_VER"
else
    MISSING+=("python3")
fi

if command -v ffmpeg &>/dev/null; then
    log_ok "ffmpeg"
else
    MISSING+=("ffmpeg")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    log_warn "缺少以下依赖:"
    for dep in "${MISSING[@]}"; do
        echo "   - $dep"
    done
    echo ""
    auto_confirm "是否自动安装？需要 sudo 权限 (y/n) " y
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v apt-get &>/dev/null; then
            PKG_MGR="apt-get"
            sudo apt-get update -qq
        elif command -v dnf &>/dev/null; then
            PKG_MGR="dnf"
        elif command -v yum &>/dev/null; then
            PKG_MGR="yum"
        else
            log_fail "未识别的包管理器，请手动安装"
            exit 1
        fi
        for dep in "${MISSING[@]}"; do
            case "$dep" in
                nodejs*)
                    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
                    sudo $PKG_MGR install -y nodejs
                    ;;
                python3) sudo $PKG_MGR install -y python3 python3-pip ;;
                ffmpeg) sudo $PKG_MGR install -y ffmpeg ;;
            esac
        done
    else
        log_fail "请先安装缺失依赖后重试"
        exit 1
    fi
fi

# ============================================
# Step 2: Install OpenClaw runtime
# ============================================
log_step "2/7" "安装 OpenClaw 运行时..."

if command -v openclaw &>/dev/null; then
    CURRENT_VER=$(openclaw --version 2>/dev/null || echo "unknown")
    log_ok "OpenClaw 已安装 ($CURRENT_VER)"
else
    log_info "安装 OpenClaw..."
    sudo npm install -g openclaw@latest
    log_ok "OpenClaw 安装完成"
fi

# ============================================
# Step 3: Deploy config
# ============================================
log_step "3/7" "创建 $BRAND 数据目录..."

if [ -d "$XYVACLAW_HOME" ]; then
    log_warn "$XYVACLAW_HOME 已存在"
    auto_confirm "  备份覆盖(y) / 合并(n) / 退出(q)? " n
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BACKUP="$HOME/.xyvaclaw.backup.$(date '+%Y%m%d_%H%M%S')"
        mv "$XYVACLAW_HOME" "$BACKUP"
        mkdir -p "$XYVACLAW_HOME"
    elif [[ $REPLY =~ ^[Qq]$ ]]; then
        exit 0
    fi
else
    mkdir -p "$XYVACLAW_HOME"
fi

for dir in agents workspace extensions config completions scripts; do
    if [ -d "$SCRIPT_DIR/config-base/$dir" ]; then
        rsync -a --ignore-existing "$SCRIPT_DIR/config-base/$dir/" "$XYVACLAW_HOME/$dir/"
        log_ok "$dir/"
    fi
done

if [ -f "$SCRIPT_DIR/config-base/openclaw.json.template" ]; then
    cp "$SCRIPT_DIR/config-base/openclaw.json.template" "$XYVACLAW_HOME/openclaw.json.template"
fi

mkdir -p "$XYVACLAW_HOME"/{workspace/memory,workspace/output/{audio,video,temp},workspace/.reasoning,workspace/state,logs,memory,sessions,cache,secrets,identity,cron,delivery-queue}

# ============================================
# Step 4: Config (wizard or manual)
# ============================================
log_step "4/7" "配置 $BRAND..."

WIZARD_DIR="$SCRIPT_DIR/setup-wizard"
USE_WIZARD=false

if [ -d "$WIZARD_DIR" ] && [ -f "$WIZARD_DIR/package.json" ]; then
    if [ "$AUTO_MODE" = true ]; then
        log_info "无人值守模式：跳过 Web 向导，使用环境变量/模板配置"
        USE_WIZARD=false
    else
        echo ""
        echo -e "  ${BOLD}选择配置方式:${NC}"
        echo "    1) Web 配置向导 (推荐)"
        echo "    2) 手动编辑 .env 文件"
        read -p "  请选择 (1/2): " -n 1 -r
        echo ""
        [[ $REPLY == "1" ]] && USE_WIZARD=true
    fi
fi

if [ "$USE_WIZARD" = true ]; then
    # Check if frontend is built (dist/ may be absent after git clone)
    NEED_BUILD=false
    if [ ! -f "$WIZARD_DIR/dist/index.html" ]; then
        NEED_BUILD=true
        log_info "前端未构建，正在安装依赖并构建..."
    fi

    # Install wizard deps if needed
    if [ ! -d "$WIZARD_DIR/node_modules" ] || [ "$(ls -A "$WIZARD_DIR/node_modules" 2>/dev/null | head -1)" = "" ]; then
        if [ "$NEED_BUILD" = true ]; then
            (cd "$WIZARD_DIR" && npm install 2>/dev/null) || {
                log_warn "npm install 失败，将使用手动配置"
                USE_WIZARD=false
            }
        else
            (cd "$WIZARD_DIR" && npm install --production 2>/dev/null) || {
                log_warn "npm install 失败，将使用手动配置"
                USE_WIZARD=false
            }
        fi
    fi

    # Build frontend if needed
    if [ "$USE_WIZARD" = true ] && [ "$NEED_BUILD" = true ]; then
        (cd "$WIZARD_DIR" && npx vite build 2>/dev/null) || {
            log_warn "前端构建失败，将使用手动配置"
            USE_WIZARD=false
        }
        if [ "$USE_WIZARD" = true ] && [ -f "$WIZARD_DIR/dist/index.html" ]; then
            log_ok "前端构建完成"
        fi
    fi
fi

if [ "$USE_WIZARD" = true ]; then
    WIZARD_CONFIG="$XYVACLAW_HOME/.wizard-config.json"
    export XYVACLAW_HOME WIZARD_CONFIG WIZARD_PORT
    node "$WIZARD_DIR/server/index.js" &
    WIZARD_PID=$!
    sleep 2
    echo -e "  配置向导: ${BOLD}http://localhost:${WIZARD_PORT}${NC}"
    if command -v xdg-open &>/dev/null; then
        xdg-open "http://localhost:${WIZARD_PORT}" 2>/dev/null || true
    fi
    wait $WIZARD_PID 2>/dev/null || true
    if [ -f "$WIZARD_CONFIG" ]; then
        cd "$XYVACLAW_HOME"
        python3 "$SCRIPT_DIR/installer/restore-config.py" \
            "$XYVACLAW_HOME/openclaw.json.template" "$XYVACLAW_HOME/.env" "$WIZARD_CONFIG"
        if [ -f "openclaw.json" ] && [ "$(pwd)" != "$XYVACLAW_HOME" ]; then
            mv openclaw.json "$XYVACLAW_HOME/openclaw.json"
        fi
    fi
else
    ENV_FILE="$XYVACLAW_HOME/.env"
    if [ ! -f "$ENV_FILE" ]; then
        cp "$SCRIPT_DIR/templates/.env.template" "$ENV_FILE"
    fi
    echo -e "  请编辑: ${BOLD}$ENV_FILE${NC}"
    echo "  必填: DEEPSEEK_API_KEY 或 BAILIAN_API_KEY"

    if [ "$AUTO_MODE" = true ]; then
        log_info "无人值守模式：从环境变量写入配置..."
        [ -n "${DEEPSEEK_API_KEY:-}" ] && sed -i "s/^DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${BAILIAN_API_KEY:-}" ] && sed -i "s/^BAILIAN_API_KEY=.*/BAILIAN_API_KEY=${BAILIAN_API_KEY}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${FEISHU_APP_ID:-}" ] && sed -i "s/^FEISHU_APP_ID=.*/FEISHU_APP_ID=${FEISHU_APP_ID}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${FEISHU_APP_SECRET:-}" ] && sed -i "s/^FEISHU_APP_SECRET=.*/FEISHU_APP_SECRET=${FEISHU_APP_SECRET}/" "$ENV_FILE" 2>/dev/null || true
        [ -n "${ASSISTANT_NAME:-}" ] && sed -i "s/^ASSISTANT_NAME=.*/ASSISTANT_NAME=${ASSISTANT_NAME}/" "$ENV_FILE" 2>/dev/null || true
        if grep -qE '^(DEEPSEEK_API_KEY|BAILIAN_API_KEY)=.+' "$ENV_FILE" 2>/dev/null; then
            log_ok "API Key 已从环境变量写入"
        else
            log_warn "未检测到 API Key，安装后请手动编辑 $ENV_FILE"
        fi
    else
        read -p "  填写完成后按回车继续..." -r
    fi

    if [ -f "$XYVACLAW_HOME/openclaw.json.template" ]; then
        cd "$XYVACLAW_HOME"
        python3 "$SCRIPT_DIR/installer/restore-config.py" \
            "$XYVACLAW_HOME/openclaw.json.template" "$ENV_FILE"
    fi
fi

# ============================================
# Step 5: Identity files
# ============================================
log_step "5/7" "生成身份文件..."

ASSISTANT_NAME="AI Assistant"
if [ -f "$XYVACLAW_HOME/.env" ]; then
    ENV_NAME=$(grep '^ASSISTANT_NAME=' "$XYVACLAW_HOME/.env" 2>/dev/null | cut -d= -f2- || true)
    [ -n "$ENV_NAME" ] && ASSISTANT_NAME="$ENV_NAME"
fi

[ -f "$SCRIPT_DIR/templates/SOUL.md.template" ] && [ ! -f "$XYVACLAW_HOME/workspace/SOUL.md" ] && \
    cp "$SCRIPT_DIR/templates/SOUL.md.template" "$XYVACLAW_HOME/workspace/SOUL.md" && log_ok "SOUL.md"

[ ! -f "$XYVACLAW_HOME/workspace/IDENTITY.md" ] && cat > "$XYVACLAW_HOME/workspace/IDENTITY.md" << EOF
# IDENTITY.md - Who I Am
- **Name:** ${ASSISTANT_NAME}
- **Platform:** xyvaClaw
- **Vibe:** Helpful, direct, and resourceful
EOF
log_ok "IDENTITY.md"

[ -f "$SCRIPT_DIR/templates/AGENTS.md.template" ] && [ ! -f "$XYVACLAW_HOME/workspace/AGENTS.md" ] && \
    cp "$SCRIPT_DIR/templates/AGENTS.md.template" "$XYVACLAW_HOME/workspace/AGENTS.md" && log_ok "AGENTS.md"

[ ! -f "$XYVACLAW_HOME/workspace/MEMORY.md" ] && echo "# MEMORY.md" > "$XYVACLAW_HOME/workspace/MEMORY.md"
[ ! -f "$XYVACLAW_HOME/workspace/USER.md" ] && echo "# USER.md" > "$XYVACLAW_HOME/workspace/USER.md"
[ ! -f "$XYVACLAW_HOME/workspace/SESSION-STATE.md" ] && echo "# Session State" > "$XYVACLAW_HOME/workspace/SESSION-STATE.md"

# ============================================
# Step 6: Install deps
# ============================================
log_step "6/7" "安装依赖..."

for ext_dir in "$XYVACLAW_HOME/extensions"/*/; do
    if [ -f "$ext_dir/package.json" ]; then
        ext_name=$(basename "$ext_dir")
        (cd "$ext_dir" && npm install --production 2>/dev/null) && log_ok "$ext_name" || log_warn "$ext_name npm install 失败"
    fi
done

SKILL_COUNT=0
for pkg_json in "$XYVACLAW_HOME/workspace/skills"/*/package.json; do
    if [ -f "$pkg_json" ]; then
        skill_dir=$(dirname "$pkg_json")
        (cd "$skill_dir" && npm install --production 2>/dev/null) && SKILL_COUNT=$((SKILL_COUNT + 1)) || true
    fi
done
[ $SKILL_COUNT -gt 0 ] && log_ok "$SKILL_COUNT 个技能 npm 依赖"

pip3 install --user edge-tts 2>/dev/null && log_ok "edge-tts" || true

# Linux path adaptations
if [ -f "$XYVACLAW_HOME/openclaw.json" ]; then
    sed -i 's|/opt/homebrew/bin/ffmpeg|/usr/bin/ffmpeg|g' "$XYVACLAW_HOME/openclaw.json" 2>/dev/null || true
    sed -i 's|/opt/homebrew/bin/ffprobe|/usr/bin/ffprobe|g' "$XYVACLAW_HOME/openclaw.json" 2>/dev/null || true
fi

# ============================================
# Step 7: Environment + systemd
# ============================================
log_step "7/7" "配置环境..."

SHELL_RC="$HOME/.bashrc"
[ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"

if ! grep -q "OPENCLAW_HOME" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# xyvaClaw" >> "$SHELL_RC"
    echo 'export OPENCLAW_HOME="$HOME/.xyvaclaw"' >> "$SHELL_RC"
    log_ok "OPENCLAW_HOME -> $SHELL_RC"
fi

# xyvaclaw wrapper
WRAPPER_PATH="/usr/local/bin/xyvaclaw"
if [ ! -f "$WRAPPER_PATH" ]; then
    sudo tee "$WRAPPER_PATH" > /dev/null << 'WRAPPER_EOF'
#!/bin/bash
export OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.xyvaclaw}"
exec openclaw "$@"
WRAPPER_EOF
    sudo chmod +x "$WRAPPER_PATH"
    log_ok "xyvaclaw 命令"
fi

# Feishu secret
if [ -f "$XYVACLAW_HOME/.env" ]; then
    FEISHU_SECRET=$(grep '^FEISHU_APP_SECRET=' "$XYVACLAW_HOME/.env" 2>/dev/null | cut -d= -f2- || true)
    if [ -n "$FEISHU_SECRET" ]; then
        echo "FEISHU_APP_SECRET=$FEISHU_SECRET" > "$XYVACLAW_HOME/secrets/feishu.env"
        chmod 600 "$XYVACLAW_HOME/secrets/feishu.env"
    fi
fi

# systemd
echo ""
auto_confirm "  是否配置 systemd 自启动？需要 sudo (y/n) " y
if [[ $REPLY =~ ^[Yy]$ ]]; then
    OPENCLAW_BIN=$(which openclaw 2>/dev/null || echo "/usr/local/bin/openclaw")
    sudo tee /etc/systemd/system/xyvaclaw.service > /dev/null << SERVICE_EOF
[Unit]
Description=xyvaClaw AI Gateway
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=${OPENCLAW_BIN} gateway
Restart=always
RestartSec=10
WorkingDirectory=$HOME
Environment=HOME=$HOME
Environment=OPENCLAW_HOME=${XYVACLAW_HOME}
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
SERVICE_EOF
    sudo systemctl daemon-reload
    sudo systemctl enable xyvaclaw
    log_ok "systemd 服务已创建"
fi

# Post-install: check for updates (anonymous)
INSTALL_MODE="interactive"
[ "$AUTO_MODE" = true ] && INSTALL_MODE="auto"
(curl -sS -m 5 -X POST "https://api.xyvaclaw.com/v1/setup-complete" \
  -H "Content-Type: application/json" \
  -d "{\"os\":\"linux\",\"v\":\"1.0.0\",\"mode\":\"${INSTALL_MODE}\"}" \
  2>/dev/null || true) &

echo ""
echo -e "${GREEN}${BOLD}  xyvaClaw 安装完成!${NC}"
echo ""
echo "  启动: xyvaclaw gateway"
echo "  或:   sudo systemctl start xyvaclaw"
echo ""

auto_confirm "  是否现在启动？(y/n) " y
if [[ $REPLY =~ ^[Yy]$ ]]; then
    export OPENCLAW_HOME="$XYVACLAW_HOME"
    if [ "$AUTO_MODE" = true ]; then
        nohup openclaw gateway > "$XYVACLAW_HOME/logs/gateway.log" 2>&1 &
        sleep 2
        echo -e "  ${GREEN}OK${NC} Gateway 已在后台启动 (PID: $!)"
    else
        openclaw gateway
    fi
fi
