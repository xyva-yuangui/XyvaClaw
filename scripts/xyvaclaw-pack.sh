#!/bin/bash
# ============================================
# xyvaClaw 打包分发脚本
# 将项目打包为可分发的 tar.gz
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
OUTPUT_DIR="${1:-$HOME/Desktop}"
PACK_NAME="xyvaclaw-${TIMESTAMP}"
ARCHIVE="$OUTPUT_DIR/${PACK_NAME}.tar.gz"

echo "🐾 xyvaClaw 打包工具"
echo "===================="
echo ""

# Verify project structure
if [ ! -f "$PROJECT_DIR/xyvaclaw-setup.sh" ]; then
    echo "❌ 未找到 xyvaClaw 项目目录"
    exit 1
fi

# Check if wizard is built
if [ ! -d "$PROJECT_DIR/setup-wizard/dist" ]; then
    echo "📦 构建配置向导前端..."
    (cd "$PROJECT_DIR/setup-wizard" && npm install && npx vite build)
fi

echo "📦 创建打包..."

cd "$PROJECT_DIR"

# Create tar.gz excluding dev files
tar -czf "$ARCHIVE" \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='.DS_Store' \
    --exclude='*.sqlite' \
    --exclude='setup-wizard/src' \
    --exclude='setup-wizard/node_modules' \
    --exclude='config-base/extensions/*/node_modules' \
    --exclude='config-base/workspace/skills/*/node_modules' \
    --exclude='config-base/workspace/skills/*/.venv' \
    --exclude='config-base/workspace/skills/*/__pycache__' \
    -C "$(dirname "$PROJECT_DIR")" \
    "$(basename "$PROJECT_DIR")"

SIZE=$(du -sh "$ARCHIVE" | cut -f1)

echo ""
echo "✅ 打包完成！"
echo "   文件: $ARCHIVE"
echo "   大小: $SIZE"
echo ""
echo "📖 分发方式:"
echo "   1. 上传到 GitHub Release"
echo "   2. 通过网盘/AirDrop/scp 分享"
echo ""
echo "📖 用户安装:"
echo "   tar -xzf $(basename "$ARCHIVE")"
echo "   cd $(basename "$PROJECT_DIR")"
echo "   bash xyvaclaw-setup.sh"
