# BOOT.md — Gateway 重启后自动执行

> 保持精简，减少启动延迟。

1. 读取 `SESSION-STATE.md` — 恢复活跃任务上下文
2. 读取 `memory/working-buffer.md` — 如有未处理的危险区日志，提取关键信息
3. 读取 `docs/todo.md` — 有紧急待办立即报告
4. 运行 `python3 ~/.openclaw/workspace/scripts/self-audit.py` — 快速健康检查
5. 通过飞书通知用户：`🟢 老贾已重启，状态正常` 或 `⚠️ 老贾已重启，发现 N 个问题`
