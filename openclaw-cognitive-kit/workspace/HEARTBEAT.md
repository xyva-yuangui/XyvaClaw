# HEARTBEAT.md

## 每次心跳（<30s）
1. 读 `docs/todo.md` → 有项就执行
2. 扫 gateway 错误日志最近20行 → 新错误记 error-tracker
3. 无异常回复 `HEARTBEAT_OK`

## 每日（首次心跳）
4. 运行自检脚本 + 确认当日 memory 已写
