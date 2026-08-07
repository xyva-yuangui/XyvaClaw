#!/bin/bash
# ============================================
# OpenClaw 一键安装脚本 (Linux - Ubuntu/Debian)
# 将打包的 OpenClaw 配置部署到 Linux 服务器
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW="$HOME/.openclaw"

echo "🐾 OpenClaw 一键安装 (Linux)"
echo "============================="
echo ""

# ---- Step 1: 检查系统环境 ----
echo "🔍 Step 1: 检查系统环境..."

MISSING=()

# Node.js
if command -v node &>/dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
        MISSING+=("nodejs (当前 $NODE_VER, 需要 22+)")
    else
        echo "  ✅ Node.js $NODE_VER"
    fi
else
    MISSING+=("nodejs")
fi

# Python 3
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    echo "  ✅ Python $PY_VER"
else
    MISSING+=("python3")
fi

# ffmpeg
if command -v ffmpeg &>/dev/null; then
    echo "  ✅ ffmpeg"
else
    MISSING+=("ffmpeg")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  缺少以下依赖:"
    for dep in "${MISSING[@]}"; do
        echo "   - $dep"
    done
    echo ""
    read -p "是否自动安装？需要 sudo 权限 (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 检测包管理器
        if command -v apt-get &>/dev/null; then
            PKG_MGR="apt"
            sudo apt-get update -qq
        elif command -v yum &>/dev/null; then
            PKG_MGR="yum"
        elif command -v dnf &>/dev/null; then
            PKG_MGR="dnf"
        else
            echo "❌ 未识别的包管理器，请手动安装依赖"
            exit 1
        fi

        for dep in "${MISSING[@]}"; do
            case "$dep" in
                nodejs*)
                    echo "📦 安装 Node.js 22..."
                    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
                    sudo $PKG_MGR install -y nodejs
                    ;;
                python3)
                    sudo $PKG_MGR install -y python3 python3-pip
                    ;;
                ffmpeg)
                    sudo $PKG_MGR install -y ffmpeg
                    ;;
            esac
        done
    else
        echo "❌ 请先安装缺失依赖后重试"
        exit 1
    fi
fi

# ---- Step 2: 安装 OpenClaw ----
echo ""
echo "📦 Step 2: 安装 OpenClaw..."

if command -v openclaw &>/dev/null; then
    CURRENT_VER=$(openclaw --version 2>/dev/null || echo "unknown")
    echo "  ✅ OpenClaw 已安装 ($CURRENT_VER)"
    read -p "  是否更新到最新版？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g openclaw@latest
    fi
else
    echo "  安装 OpenClaw..."
    sudo npm install -g openclaw@latest
fi

# ---- Step 3: 部署配置 ----
echo ""
echo "📂 Step 3: 部署配置到 ~/.openclaw..."

if [ -d "$OPENCLAW" ]; then
    echo "  ⚠️  ~/.openclaw 已存在"
    read -p "  是否备份并覆盖？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BACKUP="$HOME/.openclaw.backup.$(date '+%Y%m%d_%H%M%S')"
        echo "  📋 备份到 $BACKUP"
        mv "$OPENCLAW" "$BACKUP"
    else
        echo "  将合并到现有目录（不覆盖已有文件）"
    fi
fi

mkdir -p "$OPENCLAW"

# 复制目录结构
for dir in agents workspace cron extensions skills config subagents; do
    if [ -d "$SCRIPT_DIR/$dir" ]; then
        echo "  📋 部署 $dir/"
        rsync -a --ignore-existing "$SCRIPT_DIR/$dir/" "$OPENCLAW/$dir/"
    fi
done

# 复制额外 workspace（多角色）
for ws in "$SCRIPT_DIR"/workspace-*/; do
    if [ -d "$ws" ]; then
        ws_name=$(basename "$ws")
        echo "  📋 部署 $ws_name/"
        rsync -a --ignore-existing "$ws" "$OPENCLAW/$ws_name/"
    fi
done

# ---- Step 4: 恢复配置 ----
echo ""
echo "🔑 Step 4: 恢复配置..."

ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$SCRIPT_DIR/.env.template" ]; then
        cp "$SCRIPT_DIR/.env.template" "$ENV_FILE"
        echo "  📝 已创建 .env 模板，请填写你的密钥："
        echo "     $ENV_FILE"
        echo ""
        echo "  必填项:"
        echo "    BAILIAN_API_KEY=你的百炼API密钥"
        echo "    FEISHU_APP_SECRET=你的飞书应用密钥"
        echo ""
        read -p "  填写完成后按回车继续..." -r
    fi
fi

if [ -f "$SCRIPT_DIR/openclaw.json.sanitized" ]; then
    echo "  🔧 恢复 openclaw.json..."
    cd "$SCRIPT_DIR"
    python3 restore-config.py openclaw.json.sanitized "$ENV_FILE" --package "$OPENCLAW"
    mv openclaw.json "$OPENCLAW/openclaw.json"
else
    echo "  ❌ 未找到 openclaw.json.sanitized，无法恢复配置"
    exit 1
fi

# ---- Step 5: Linux 路径适配 ----
echo ""
echo "🔧 Step 5: Linux 路径适配..."

# 源机硬编码用户路径 → 目标机 $HOME
ADAPTED=0
while IFS= read -r f; do
    LC_ALL=C sed -i "s|__LEGACY_HOME__|$HOME|g" "$f" && ADAPTED=$((ADAPTED+1))
done < <(LC_ALL=C grep -rl --exclude-dir=node_modules --exclude='*.db' --exclude='*.sqlite*' '__LEGACY_HOME__' "$OPENCLAW" 2>/dev/null)
echo "  ✅ 已适配 $ADAPTED 个文件的硬编码用户路径"

# 修复指向源机绝对路径的符号链接
SYMFIX=0
while IFS= read -r link; do
    target=$(readlink "$link")
    case "$target" in
        /Users/*/.openclaw/*|/home/*/.openclaw/*)
            newtarget="$OPENCLAW/${target#*/.openclaw/}"
            if [ -e "$newtarget" ]; then
                ln -sfn "$newtarget" "$link" && SYMFIX=$((SYMFIX+1))
            fi
            ;;
    esac
done < <(find "$OPENCLAW" -type l -not -path '*/node_modules/*' 2>/dev/null)
[ "$SYMFIX" -gt 0 ] && echo "  ✅ 已修复 $SYMFIX 个绝对路径符号链接"

# 替换 macOS 特有的路径
if [ -f "$OPENCLAW/openclaw.json" ]; then
    # ffmpeg 路径
    sed -i 's|/opt/homebrew/bin/ffmpeg|/usr/bin/ffmpeg|g' "$OPENCLAW/openclaw.json" 2>/dev/null || true
    sed -i 's|/opt/homebrew/bin/ffprobe|/usr/bin/ffprobe|g' "$OPENCLAW/openclaw.json" 2>/dev/null || true
fi

# 适配所有 Python 脚本中的 ffmpeg 路径
find "$OPENCLAW/workspace" -name "*.py" -exec \
    sed -i "s|/opt/homebrew/bin/ffmpeg|$(which ffmpeg)|g" {} \; 2>/dev/null || true
find "$OPENCLAW/workspace" -name "*.py" -exec \
    sed -i "s|/opt/homebrew/bin/ffprobe|$(which ffprobe)|g" {} \; 2>/dev/null || true

# 适配 screencapture（Linux 用 scrot 或 gnome-screenshot）
if command -v scrot &>/dev/null; then
    SCREENSHOT_CMD="scrot"
elif command -v gnome-screenshot &>/dev/null; then
    SCREENSHOT_CMD="gnome-screenshot"
else
    SCREENSHOT_CMD="echo 'No screenshot tool available'"
fi
echo "  📸 截图工具: $SCREENSHOT_CMD"

echo "  ✅ 路径适配完成"

# ---- Step 6: 创建目录 + Python 依赖 ----
echo ""
echo "📁 Step 6: 创建运行时目录..."
mkdir -p "$OPENCLAW/workspace/memory"
mkdir -p "$OPENCLAW/workspace/output/audio"
mkdir -p "$OPENCLAW/workspace/output/video"
mkdir -p "$OPENCLAW/workspace/output/temp"
mkdir -p "$OPENCLAW/workspace/.reasoning"
mkdir -p "$OPENCLAW/workspace/state"
mkdir -p "$OPENCLAW/logs"
mkdir -p "$OPENCLAW/memory"

echo "🐍 安装 Python 依赖..."
pip3 install --user edge-tts 2>/dev/null && echo "  ✅ edge-tts" || echo "  ⚠️ edge-tts 安装失败"
if [ -f "$OPENCLAW/workspace/requirements.txt" ]; then
    echo "  📦 安装 workspace/requirements.txt（可能需要几分钟）..."
    pip3 install --user -r "$OPENCLAW/workspace/requirements.txt" 2>/dev/null \
        && echo "  ✅ requirements.txt 安装完成" \
        || echo "  ⚠️ 部分依赖安装失败，可稍后手动执行: pip3 install -r ~/.openclaw/workspace/requirements.txt"
fi

# ---- Step 7: npm 依赖 ----
echo ""
echo "📦 Step 7: 安装技能 npm 依赖..."
for pkg_json in "$OPENCLAW/workspace/skills"/*/package.json; do
    if [ -f "$pkg_json" ]; then
        skill_dir=$(dirname "$pkg_json")
        skill_name=$(basename "$skill_dir")
        echo "  📦 $skill_name..."
        (cd "$skill_dir" && npm install --production 2>/dev/null) || echo "  ⚠️ $skill_name npm install 失败"
    fi
done

# 扩展依赖（包内不携带 node_modules，含平台相关原生二进制，必须目标机重建）
echo "📦 安装扩展 npm 依赖..."
for pkg_json in "$OPENCLAW/extensions"/*/package.json; do
    if [ -f "$pkg_json" ]; then
        ext_dir=$(dirname "$pkg_json")
        ext_name=$(basename "$ext_dir")
        echo "  📦 $ext_name..."
        (cd "$ext_dir" && npm install --production 2>/dev/null) || echo "  ⚠️ $ext_name npm install 失败"
    fi
done

# ---- Step 8: systemd 服务 ----
echo ""
echo "🚀 Step 8: 配置 systemd 服务..."

SERVICE_FILE="/etc/systemd/system/openclaw.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "  ✅ systemd 服务已存在"
else
    read -p "  是否配置 systemd 自启动？需要 sudo (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        OPENCLAW_BIN=$(which openclaw)
        sudo tee "$SERVICE_FILE" > /dev/null <<SERVICE
[Unit]
Description=OpenClaw AI Gateway
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=${OPENCLAW_BIN} gateway
Restart=always
RestartSec=10
WorkingDirectory=$HOME
Environment=HOME=$HOME
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
SERVICE
        sudo systemctl daemon-reload
        sudo systemctl enable openclaw
        echo "  ✅ systemd 服务已创建并启用"
        echo "  启动: sudo systemctl start openclaw"
        echo "  状态: sudo systemctl status openclaw"
    fi
fi

# ---- 完成 ----
echo ""
echo "🎉 安装完成！"
echo ""
echo "📖 下一步:"
echo "  1. 启动: openclaw gateway (或 sudo systemctl start openclaw)"
echo "  2. 状态: openclaw gateway status"
echo "  3. 绑定: openclaw agents list --bindings"
echo ""
echo "⚠️  注意事项:"
echo "  - 首次启动会下载本地 embedding 模型（约 70MB）"
echo "  - 飞书需要在开放平台配置 webhook 回调地址指向此服务器"
echo "  - 确保端口 18789 可访问（或配置反向代理）"
echo ""
echo "🐾 Enjoy your AI assistant!"
