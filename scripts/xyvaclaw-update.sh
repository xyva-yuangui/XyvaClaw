#!/bin/bash
# ============================================
# xyvaClaw 自更新脚本
# 更新 OpenClaw 运行时 + xyvaClaw 配置
# ============================================
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

XYVACLAW_HOME="${XYVACLAW_HOME:-$HOME/.xyvaclaw}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BOLD}🐾 xyvaClaw 更新工具${NC}"
echo "========================"
echo ""

# Step 1: Update OpenClaw runtime
echo -e "${BLUE}[1/4]${NC} 检查 OpenClaw 运行时更新..."
CURRENT_VER=$(openclaw --version 2>/dev/null || echo "unknown")
echo "  当前版本: $CURRENT_VER"

read -p "  是否更新 OpenClaw 运行时？(y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  更新中..."
    npm update -g openclaw 2>/dev/null || sudo npm update -g openclaw
    NEW_VER=$(openclaw --version 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✅${NC} 更新到 $NEW_VER"
else
    echo "  跳过"
fi

# Step 2: Update xyvaClaw project (if git repo)
echo ""
echo -e "${BLUE}[2/4]${NC} 检查 xyvaClaw 项目更新..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    REMOTE_STATUS=$(git remote update 2>/dev/null && git status -uno 2>/dev/null | grep -c "behind" || echo "0")
    if [ "$REMOTE_STATUS" -gt 0 ]; then
        echo "  有新版本可用"
        read -p "  是否拉取更新？(y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git pull --rebase
            echo -e "  ${GREEN}✅${NC} 项目已更新"
        fi
    else
        echo -e "  ${GREEN}✅${NC} 已是最新版本"
    fi
else
    echo "  项目不是 Git 仓库，跳过"
fi

# Step 3: Update extensions
echo ""
echo -e "${BLUE}[3/4]${NC} 更新扩展依赖..."
for ext_dir in "$XYVACLAW_HOME/extensions"/*/; do
    if [ -f "$ext_dir/package.json" ]; then
        ext_name=$(basename "$ext_dir")
        echo "  更新 $ext_name..."
        (cd "$ext_dir" && npm update --production 2>/dev/null) && echo -e "  ${GREEN}✅${NC} $ext_name" || echo -e "  ${YELLOW}⚠️${NC} $ext_name 更新失败"
    fi
done

# Step 4: Restart gateway
echo ""
echo -e "${BLUE}[4/4]${NC} 重启 gateway..."

# Check if gateway is running
if pgrep -f "openclaw.*gateway" > /dev/null 2>&1; then
    read -p "  Gateway 正在运行，是否重启？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$(uname)" = "Darwin" ]; then
            launchctl kickstart -k "gui/$(id -u)/ai.xyvaclaw.gateway" 2>/dev/null || {
                echo "  LaunchAgent 重启失败，尝试手动重启..."
                pkill -f "openclaw.*gateway" 2>/dev/null || true
                sleep 2
                OPENCLAW_HOME="$XYVACLAW_HOME" nohup openclaw gateway > /dev/null 2>&1 &
            }
        else
            sudo systemctl restart xyvaclaw 2>/dev/null || {
                pkill -f "openclaw.*gateway" 2>/dev/null || true
                sleep 2
                OPENCLAW_HOME="$XYVACLAW_HOME" nohup openclaw gateway > /dev/null 2>&1 &
            }
        fi
        echo -e "  ${GREEN}✅${NC} Gateway 已重启"
    fi
else
    echo "  Gateway 未在运行"
fi

echo ""
echo -e "${GREEN}${BOLD}更新完成！${NC}"
