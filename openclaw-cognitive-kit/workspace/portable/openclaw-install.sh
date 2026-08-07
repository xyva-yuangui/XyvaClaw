#!/bin/bash
# ============================================
# OpenClaw 一键安装脚本 (macOS)
# 将打包的 OpenClaw 配置部署到新 Mac
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW="$HOME/.openclaw"

echo "🐾 OpenClaw 一键安装 (macOS)"
echo "============================"
echo ""

# ---- Step 1: 检查系统环境 ----
echo "🔍 Step 1: 检查系统环境..."

MISSING=()

# Node.js
if command -v node &>/dev/null; then
    NODE_VER=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -lt 22 ]; then
        MISSING+=("node (当前 $NODE_VER, 需要 22+)")
    else
        echo "  ✅ Node.js $NODE_VER"
    fi
else
    MISSING+=("node")
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

# Homebrew
if command -v brew &>/dev/null; then
    echo "  ✅ Homebrew"
else
    MISSING+=("homebrew")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  缺少以下依赖:"
    for dep in "${MISSING[@]}"; do
        echo "   - $dep"
    done
    echo ""
    read -p "是否自动安装？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 安装 Homebrew
        if ! command -v brew &>/dev/null; then
            echo "📦 安装 Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        # 安装缺失的依赖
        for dep in "${MISSING[@]}"; do
            case "$dep" in
                node*) brew install node ;;
                python3) brew install python ;;
                ffmpeg) brew install ffmpeg ;;
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
    npm install -g openclaw@latest
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

# 检查 .env 文件
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

# 恢复配置（openclaw.json + agents/ + tushare.json）
if [ -f "$SCRIPT_DIR/openclaw.json.sanitized" ]; then
    echo "  🔧 恢复 openclaw.json..."
    cd "$SCRIPT_DIR"
    python3 restore-config.py openclaw.json.sanitized "$ENV_FILE" --package "$OPENCLAW"
    mv openclaw.json "$OPENCLAW/openclaw.json"
else
    echo "  ❌ 未找到 openclaw.json.sanitized，无法恢复配置"
    exit 1
fi

# ---- Step 4.5: 源机硬编码路径适配 ----
# 历史脚本/plist/配置中硬编码了源机用户目录，统一替换为目标机 $HOME
echo ""
echo "🔧 Step 4.5: 适配硬编码用户路径..."
ADAPTED=0
while IFS= read -r f; do
    # LC_ALL=C 避免 macOS sed 对非 UTF-8 字节报 illegal byte sequence
    LC_ALL=C sed -i '' "s|__LEGACY_HOME__|$HOME|g" "$f" && ADAPTED=$((ADAPTED+1))
done < <(LC_ALL=C grep -rl --exclude-dir=node_modules --exclude='*.db' --exclude='*.sqlite*' '__LEGACY_HOME__' "$OPENCLAW" 2>/dev/null)
echo "  ✅ 已适配 $ADAPTED 个文件的硬编码路径"

# 修复指向源机绝对路径的符号链接（sed 改不了链接目标）
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

# ---- Step 5: 创建必要目录 ----
echo ""
echo "📁 Step 5: 创建运行时目录..."
mkdir -p "$OPENCLAW/workspace/memory"
mkdir -p "$OPENCLAW/workspace/output/audio"
mkdir -p "$OPENCLAW/workspace/output/video"
mkdir -p "$OPENCLAW/workspace/output/temp"
mkdir -p "$OPENCLAW/workspace/.reasoning"
mkdir -p "$OPENCLAW/workspace/state"
mkdir -p "$OPENCLAW/logs"
mkdir -p "$OPENCLAW/memory"
echo "  ✅ 目录创建完成"

# ---- Step 6: 安装 Python 依赖 ----
echo ""
echo "🐍 Step 6: 安装 Python 依赖..."
pip3 install --user edge-tts 2>/dev/null && echo "  ✅ edge-tts" || echo "  ⚠️ edge-tts 安装失败"
if [ -f "$OPENCLAW/workspace/requirements.txt" ]; then
    echo "  📦 安装 workspace/requirements.txt（量化/可视化/自动化依赖，可能需要几分钟）..."
    pip3 install --user -r "$OPENCLAW/workspace/requirements.txt" 2>/dev/null \
        && echo "  ✅ requirements.txt 安装完成" \
        || echo "  ⚠️ 部分依赖安装失败，可稍后手动执行: pip3 install -r ~/.openclaw/workspace/requirements.txt"
fi

# ---- Step 7: 安装 npm 依赖（技能 + 扩展） ----
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

# ---- Step 8: 配置自启动 ----
echo ""
echo "🚀 Step 8: 配置开机自启动..."

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/ai.openclaw.gateway.plist"

if [ -f "$PLIST_FILE" ]; then
    echo "  ✅ LaunchAgent 已存在"
else
    read -p "  是否配置开机自启动？(y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        mkdir -p "$PLIST_DIR"
        OPENCLAW_BIN=$(which openclaw)
        cat > "$PLIST_FILE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.openclaw.gateway</string>
    <key>ProgramArguments</key>
    <array>
        <string>${OPENCLAW_BIN}</string>
        <string>gateway</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OPENCLAW}/logs/gateway.log</string>
    <key>StandardErrorPath</key>
    <string>${OPENCLAW}/logs/gateway.err.log</string>
</dict>
</plist>
PLIST
        echo "  ✅ LaunchAgent 已创建: $PLIST_FILE"
    fi
fi

# ---- Step 9: 首次运行 ----
echo ""
echo "🎉 安装完成！"
echo ""
echo "📖 下一步:"
echo "  1. 启动 OpenClaw: openclaw gateway"
echo "  2. 检查状态: openclaw gateway status"
echo "  3. 查看绑定: openclaw agents list --bindings"
echo ""
echo "⚠️  注意事项:"
echo "  - 首次启动会下载本地 embedding 模型（约 70MB）"
echo "  - 飞书需要在开放平台配置 webhook 回调地址"
echo "  - 小红书 Cookie 需要重新获取（会过期）"
echo ""
echo "🐾 Enjoy your AI assistant!"
