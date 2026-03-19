# HEARTBEAT.md

> 完整说明 → `playbooks/heartbeat-reference.md`

## 每次心跳（<30s）
1. 读 `docs/todo.md` → 有项就执行
2. 扫 `gateway.err.log` 最近20行 → 新错误记error-tracker
3. 无异常回复 `HEARTBEAT_OK`

## 每日（首次心跳）
4. `python3 scripts/self-audit.py` + 确认当日memory已写
5. SESSION-STATE.md >24h → 清理
6. 交易日9:30-15:00 → 检查选股推送

## Cron规范
- 提醒用agentTurn+announce，后台用systemEvent+none
- 时区必须Asia/Shanghai，长任务设timeoutMs
- 详细规范 → `playbooks/heartbeat-reference.md`
