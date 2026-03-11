#!/bin/bash
# OpenClaw log rotation script
# Recommended cron: 0 4 * * * ~/.xyvaclaw/scripts/log-rotate.sh

LOG_DIR="$HOME/.openclaw/logs"
MAX_SIZE_MB=50
ARCHIVE_DAYS=7

rotate_log() {
  local file="$1"
  if [ ! -f "$file" ]; then return; fi
  
  local size_bytes
  size_bytes=$(stat -f%z "$file" 2>/dev/null || echo 0)
  local size_mb=$((size_bytes / 1024 / 1024))
  
  if [ "$size_mb" -ge "$MAX_SIZE_MB" ]; then
    local timestamp
    timestamp=$(date +%Y%m%d-%H%M%S)
    local rotated="${file}.${timestamp}"
    cp "$file" "$rotated"
    : > "$file"
    # Compress old log
    gzip "$rotated" 2>/dev/null
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Rotated $file (${size_mb}MB) -> ${rotated}.gz"
  fi
}

# Clean up old rotated logs
find "$LOG_DIR" -name "*.gz" -mtime +$ARCHIVE_DAYS -delete 2>/dev/null

# Rotate main logs
rotate_log "$LOG_DIR/gateway.log"
rotate_log "$LOG_DIR/gateway.err.log"
rotate_log "$LOG_DIR/git-backup.log"
rotate_log "$LOG_DIR/git-backup.err.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log rotation check complete"
