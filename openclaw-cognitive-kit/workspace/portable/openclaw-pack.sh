#!/bin/bash
# ============================================
# OpenClaw 打包脚本
# 将当前 ~/.openclaw 的配置和工作区打包为可迁移包
# ============================================
set -euo pipefail

OPENCLAW="$HOME/.openclaw"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
OUTPUT_DIR="${1:-$HOME/Desktop}"
PACK_NAME="openclaw-portable-${TIMESTAMP}"
PACK_DIR="$OUTPUT_DIR/$PACK_NAME"
ARCHIVE="$OUTPUT_DIR/${PACK_NAME}.tar.gz"

echo "🔧 OpenClaw 打包工具"
echo "===================="

# 检查 openclaw 目录
if [ ! -d "$OPENCLAW" ]; then
    echo "❌ 未找到 ~/.openclaw 目录"
    exit 1
fi

echo "📦 创建打包目录: $PACK_DIR"
mkdir -p "$PACK_DIR"

# ---- 复制可迁移文件 ----

echo "📋 复制配置文件..."
# openclaw.json（临时复制，脱敏后删除原件，包内不保留明文密钥版本）
cp "$OPENCLAW/openclaw.json" "$PACK_DIR/openclaw.json.original"

# models.json（如有）
[ -f "$OPENCLAW/models.json" ] && cp "$OPENCLAW/models.json" "$PACK_DIR/models.json.original"

echo "📋 复制 agents 目录..."
if [ -d "$OPENCLAW/agents" ]; then
    rsync -a --exclude='sessions/' --exclude='*.sqlite' \
        "$OPENCLAW/agents/" "$PACK_DIR/agents/"
fi

echo "📋 复制 workspace..."
rsync -a \
    --exclude='node_modules/' \
    --exclude='.git/' \
    --exclude='cache/' \
    --exclude='__pycache__/' \
    --exclude='.cache/' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite-shm' \
    --exclude='*.sqlite-wal' \
    --exclude='*.db-shm' \
    --exclude='*.db-wal' \
    --exclude='*memory-index*.db' \
    --exclude='*memory-vectors*.db' \
    --exclude='*conversation-buffer*.db' \
    --exclude='*llm-cache*.db' \
    --exclude='*embedding-cache*.db' \
    --exclude='lcm.db' \
    --exclude='cookies/' \
    --exclude='_backup/' \
    --exclude='venv/' \
    --exclude='.venv/' \
    --exclude='pdf_venv/' \
    --exclude='lean-venv/' \
    --exclude='output/' \
    --exclude='.wal/' \
    "$OPENCLAW/workspace/" "$PACK_DIR/workspace/"

echo "📋 复制 cron 配置..."
[ -d "$OPENCLAW/cron" ] && rsync -a "$OPENCLAW/cron/" "$PACK_DIR/cron/"

echo "📋 复制 extensions..."
# node_modules 含平台相关原生二进制，不随包迁移，安装时 npm install 重建
[ -d "$OPENCLAW/extensions" ] && rsync -a --exclude='node_modules/' --exclude='.git/' "$OPENCLAW/extensions/" "$PACK_DIR/extensions/"

echo "📋 复制 skills 注册..."
[ -d "$OPENCLAW/skills" ] && rsync -a "$OPENCLAW/skills/" "$PACK_DIR/skills/"

echo "📋 复制 config..."
[ -d "$OPENCLAW/config" ] && rsync -a "$OPENCLAW/config/" "$PACK_DIR/config/"

echo "📋 复制 subagents..."
[ -d "$OPENCLAW/subagents" ] && rsync -a "$OPENCLAW/subagents/" "$PACK_DIR/subagents/"

# 复制额外 workspace（多角色）
for ws in "$OPENCLAW"/workspace-*/; do
    if [ -d "$ws" ]; then
        ws_name=$(basename "$ws")
        echo "📋 复制 $ws_name..."
        rsync -a --exclude='node_modules/' --exclude='cache/' \
            "$ws" "$PACK_DIR/$ws_name/"
    fi
done

# ---- 脱敏 ----
echo "🔒 脱敏敏感信息..."
python3 "$OPENCLAW/workspace/portable/sanitize-config.py" \
    "$PACK_DIR/openclaw.json.original" \
    "$PACK_DIR/openclaw.json.sanitized"

# 删除明文原件，包内只保留脱敏版（同用户迁移也走 .env 恢复流程）
rm -f "$PACK_DIR/openclaw.json.original" "$PACK_DIR/models.json.original"

# 全仓密钥清洗（agents/auth-profiles、models.json、脚本/文档中硬编码密钥、cookies 等）
python3 "$OPENCLAW/workspace/portable/scrub-secrets.py" "$PACK_DIR"

# 最终关卡：仍能检出疑似密钥则中止打包
echo "🔍 打包前密钥复检..."
if ! python3 "$OPENCLAW/workspace/portable/scrub-secrets.py" "$PACK_DIR" --check; then
    echo "❌ 复检发现疑似密钥，已中止打包！请检查上方列表"
    exit 1
fi

# ---- 复制安装工具 ----
echo "📋 复制安装工具..."
cp "$OPENCLAW/workspace/portable/openclaw-install.sh" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/openclaw-install-linux.sh" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/sanitize-config.py" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/scrub-secrets.py" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/restore-config.py" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/.env.template" "$PACK_DIR/"
cp "$OPENCLAW/workspace/portable/README.md" "$PACK_DIR/"

chmod +x "$PACK_DIR/openclaw-install.sh"
chmod +x "$PACK_DIR/openclaw-install-linux.sh"

# ---- 打包 ----
echo "📦 压缩打包..."
cd "$OUTPUT_DIR"
tar -czf "$ARCHIVE" "$PACK_NAME"

# 清理临时目录
rm -rf "$PACK_DIR"

SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo ""
echo "✅ 打包完成！"
echo "   文件: $ARCHIVE"
echo "   大小: $SIZE"
echo ""
echo "📖 下一步:"
echo "   1. 将 $ARCHIVE 复制到目标电脑"
echo "   2. 解压: tar -xzf $(basename "$ARCHIVE")"
echo "   3. Mac: bash openclaw-install.sh"
echo "      Linux: bash openclaw-install-linux.sh"
echo "   4. 按提示填写 API 密钥"
