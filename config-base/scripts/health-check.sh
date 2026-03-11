#!/bin/bash
# OpenClaw gateway health check script
# Recommended cron: */10 * * * * ~/.xyvaclaw/scripts/health-check.sh

LOG_FILE="$HOME/.openclaw/logs/healthcheck.log"
GATEWAY_PORT=18789
MAX_LOG_LINES=500

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Trim healthcheck log if too long
if [ -f "$LOG_FILE" ]; then
  lines=$(wc -l < "$LOG_FILE")
  if [ "$lines" -gt "$MAX_LOG_LINES" ]; then
    tail -n 200 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
  fi
fi

# Check gateway process
GATEWAY_PID=$(pgrep -x "openclaw-gateway" 2>/dev/null || pgrep -f "openclaw/dist/index.js gateway" 2>/dev/null | head -1)
if [ -z "$GATEWAY_PID" ]; then
  log "ALERT: Gateway process not found! Attempting recovery..."
  launchctl kickstart -k gui/$(id -u)/ai.openclaw.gateway 2>&1 | while read line; do log "  recovery: $line"; done
  sleep 5
  GATEWAY_PID=$(pgrep -x "openclaw-gateway" 2>/dev/null || pgrep -f "openclaw/dist/index.js gateway" 2>/dev/null | head -1)
  if [ -z "$GATEWAY_PID" ]; then
    log "CRITICAL: Gateway recovery failed!"
  else
    log "OK: Gateway recovered, new PID=$GATEWAY_PID"
  fi
else
  # Check if gateway is responsive via HTTP
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:${GATEWAY_PORT}/" 2>/dev/null)
  if [ "$HTTP_CODE" = "000" ] || [ -z "$HTTP_CODE" ]; then
    log "WARN: Gateway PID=$GATEWAY_PID exists but HTTP probe failed (code=$HTTP_CODE)"
  else
    # Check error log growth rate
    ERR_LOG="$HOME/.openclaw/logs/gateway.err.log"
    if [ -f "$ERR_LOG" ]; then
      RECENT_ERRORS=$(tail -100 "$ERR_LOG" | grep -c "FailoverError\|completeSimple error\|No API key" 2>/dev/null)
      if [ "$RECENT_ERRORS" -gt 10 ]; then
        log "WARN: High error rate in last 100 lines: ${RECENT_ERRORS} LLM errors"
      fi
    fi
    log "OK: Gateway PID=$GATEWAY_PID HTTP=$HTTP_CODE"
  fi
fi

# Check disk space for logs
LOG_SIZE_MB=$(du -sm "$HOME/.openclaw/logs" 2>/dev/null | awk '{print $1}')
if [ "${LOG_SIZE_MB:-0}" -gt 200 ]; then
  log "WARN: Log directory is ${LOG_SIZE_MB}MB, consider running log-rotate.sh"
fi
