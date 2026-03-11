---
name: cron-scheduler
description: 用自然语言意图管理 OpenClaw 定时任务。支持创建、查询、启停、失败诊断、审计优化建议。
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["scheduling", "cron-jobs", "automation"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "⏰", "category": "tools", "priority": "medium"}
---

# Cron Scheduler

## 适用场景

- 用户说“每天9点提醒我开会”“每周一早上发周报”
- 用户说“看看哪些cron失败了”“暂停某个任务”
- 需要对 `cron/jobs.json` 做健康审计与优化建议

## 命令

### 1) 创建任务（推荐）

```bash
python3 skills/cron-scheduler/scripts/cron_helper.py create \
  --name "每日提醒" \
  --cron "0 9 * * *" \
  --message "提醒我查看任务" \
  --delivery announce \
  --to "chat:oc_xxx"
```

一次性任务：

```bash
python3 skills/cron-scheduler/scripts/cron_helper.py create \
  --name "一次性提醒" \
  --at "2026-03-15T01:00:00Z" \
  --message "提醒内容"
```

### 2) 查询任务

```bash
python3 skills/cron-scheduler/scripts/cron_helper.py status
python3 skills/cron-scheduler/scripts/cron_helper.py failures
```

### 3) 启停与手动触发

```bash
python3 skills/cron-scheduler/scripts/cron_helper.py disable --id <job_id>
python3 skills/cron-scheduler/scripts/cron_helper.py enable --id <job_id>
python3 skills/cron-scheduler/scripts/cron_helper.py run --id <job_id>
```

### 4) 审计优化

```bash
python3 skills/cron-scheduler/scripts/cron_audit.py
```

## 设计原则

- 薄封装：不重写调度引擎，只封装 `openclaw cron` CLI
- 性能优先：仅按需执行，不常驻，不新增后台进程
- 安全默认：默认 `sessionTarget=isolated`、低价值任务默认 `delivery=none`
- 时区明确：默认 `Asia/Shanghai`
