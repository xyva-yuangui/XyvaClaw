#!/usr/bin/env python3
"""
V15 永驻循环控制器 — 合并多个分散 Cron 为统一入口
全新开发, 合并:
  --daily: 自我反思 + 综合监控 + 进化日记 + 涌现扫描 + 能力自测 + 自传快照
  --tick:  主动心跳(每20min) + 自动运行监控(每4h) + 集群保活Ping
  --health: 自愈扫描(每6h) + API Fallback检查 + 能力与Cron扫描

预期: Cron 从 ~27 个减少到 ~15 个

CLI:
  python3 scripts/v15/daemon-loop-v15.py --daily
  python3 scripts/v15/daemon-loop-v15.py --tick
  python3 scripts/v15/daemon-loop-v15.py --health
  python3 scripts/v15/daemon-loop-v15.py --status
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
SCRIPTS_DIR = WORKSPACE / "scripts"
V15_DIR = SCRIPTS_DIR / "v15"
STATE_DIR = WORKSPACE / "state"
DAEMON_DB = STATE_DIR / "v15-daemon-loop.db"
DAEMON_LOG = STATE_DIR / "v15-daemon-loop.log"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据库
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Schedule Registry — 声明式任务注册
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCHEDULE_REGISTRY = {
    "daily": [
        {"name": "自校准-每日", "script": "self-calibration-v15.py", "args": ["--daily"], "timeout": 180, "retry": 1, "critical": True},
        {"name": "学习循环-每日", "script": "learning-loop-v15.py", "args": ["--daily"], "timeout": 180, "retry": 1, "critical": True},
        {"name": "规则挖掘-每日", "script": "rule-miner-v15.py", "args": ["--daily"], "timeout": 120, "retry": 1, "critical": False},
        {"name": "技能扫描", "script": "skill-forge-v15.py", "args": ["--scan"], "timeout": 60, "retry": 0, "critical": False},
        {"name": "感知健康", "script": "sense-bus-v15.py", "args": ["--health"], "timeout": 60, "retry": 0, "critical": False},
        {"name": "先知扫描", "script": "prescience-v15.py", "args": ["--scan"], "timeout": 60, "retry": 0, "critical": False},
        {"name": "轨迹维护", "script": "trajectory-recorder-v15.py", "args": ["--stats"], "timeout": 30, "retry": 0, "critical": False},
    ],
    "tick": [
        {"name": "集群保活", "script": "cluster-client-v15.py", "args": ["--test"], "timeout": 30, "retry": 2, "critical": False},
        {"name": "感知心跳", "script": "sense-bus-v15.py", "args": ["--tick"], "timeout": 30, "retry": 0, "critical": False},
        {"name": "事件源扫描", "script": "sense-bus-v15.py", "args": ["--scan"], "timeout": 30, "retry": 0, "critical": False},
        {"name": "先知预取", "script": "prescience-v15.py", "args": ["--prefetch"], "timeout": 30, "retry": 1, "critical": False},
    ],
    "health": [
        {"name": "集群连通", "script": "cluster-client-v15.py", "args": ["--test"], "timeout": 30, "retry": 2, "critical": True},
        {"name": "LLM Router", "script": "llm-router-v15.py", "args": ["--route", "健康检查测试"], "timeout": 30, "retry": 1, "critical": True},
        {"name": "感知健康", "script": "sense-bus-v15.py", "args": ["--health"], "timeout": 60, "retry": 0, "critical": False},
        {"name": "技能锻造", "script": "skill-forge-v15.py", "args": ["--health"], "timeout": 60, "retry": 0, "critical": False},
        {"name": "认知核心", "script": "cognitive-core-v15.py", "args": ["--status"], "timeout": 60, "retry": 0, "critical": False},
    ],
}

# Circuit Breaker 状态: task_name → {consecutive_failures, last_failure, tripped}
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_RESET_MINUTES = 30

# Self-Heal Actions
SELF_HEAL_ACTIONS = {
    "stale_db": {
        "description": "VACUUM stale SQLite databases",
        "action": "vacuum_db",
    },
    "oversized_db": {
        "description": "Cleanup old records in oversized databases",
        "action": "cleanup_old_records",
    },
    "missing_state_dir": {
        "description": "Recreate missing state directory",
        "action": "recreate_state_dir",
    },
    "stale_log": {
        "description": "Truncate oversized daemon log",
        "action": "truncate_log",
    },
    "consecutive_failures": {
        "description": "Reset circuit breaker after cooldown",
        "action": "reset_circuit_breaker",
    },
}


def _get_db() -> sqlite3.Connection:
    os.makedirs(STATE_DIR, exist_ok=True)
    db = sqlite3.connect(str(DAEMON_DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT,
            task TEXT,
            status TEXT,
            message TEXT,
            duration_ms INTEGER,
            retries INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_mode ON runs(mode)
    """)
    # migrate: add retries column if missing
    try:
        db.execute("ALTER TABLE runs ADD COLUMN retries INTEGER DEFAULT 0")
    except Exception:
        pass  # column already exists
    db.execute("""
        CREATE TABLE IF NOT EXISTS circuit_breakers (
            task_name TEXT PRIMARY KEY,
            consecutive_failures INTEGER DEFAULT 0,
            last_failure TEXT,
            tripped INTEGER DEFAULT 0,
            tripped_at TEXT
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS self_heal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            target TEXT,
            result TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.commit()
    return db


def _record(db: sqlite3.Connection, mode: str, task: str, status: str,
            message: str = "", duration_ms: int = 0, retries: int = 0):
    db.execute(
        "INSERT INTO runs (mode, task, status, message, duration_ms, retries) VALUES (?, ?, ?, ?, ?, ?)",
        (mode, task, status, message, duration_ms, retries)
    )
    db.commit()


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(DAEMON_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 子任务运行器
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _run_script(script_path: str, args: list = None, timeout: int = 120) -> dict:
    """运行子脚本, 返回 {ok, output, duration_ms}"""
    full_path = SCRIPTS_DIR / script_path if not os.path.isabs(script_path) else Path(script_path)
    if not full_path.exists():
        return {"ok": False, "output": f"脚本不存在: {full_path}", "duration_ms": 0}

    cmd = [sys.executable, str(full_path)] + (args or [])
    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "OPENCLAW_WORKSPACE": str(WORKSPACE)}
        )
        duration_ms = int((time.time() - start) * 1000)
        output = result.stdout[:2000] if result.stdout else ""
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr] {result.stderr[:500]}"
        return {
            "ok": result.returncode == 0,
            "output": output.strip(),
            "duration_ms": duration_ms,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": f"超时 ({timeout}s)", "duration_ms": timeout * 1000}
    except Exception as e:
        return {"ok": False, "output": str(e), "duration_ms": int((time.time() - start) * 1000)}


def _run_v15(script_name: str, args: list = None, timeout: int = 120) -> dict:
    """运行 V15 子模块脚本"""
    return _run_script(f"v15/{script_name}", args, timeout)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Circuit Breaker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _is_circuit_tripped(db: sqlite3.Connection, task_name: str) -> bool:
    """Check if circuit breaker is tripped for a task"""
    row = db.execute(
        "SELECT tripped, tripped_at FROM circuit_breakers WHERE task_name=?", (task_name,)
    ).fetchone()
    if not row or not row[0]:
        return False
    # Auto-reset after cooldown
    tripped_at = row[1]
    if tripped_at:
        try:
            tripped_time = datetime.fromisoformat(tripped_at)
            if datetime.now() - tripped_time > timedelta(minutes=CIRCUIT_BREAKER_RESET_MINUTES):
                db.execute(
                    "UPDATE circuit_breakers SET tripped=0, consecutive_failures=0 WHERE task_name=?",
                    (task_name,)
                )
                db.commit()
                _log(f"    ⚡ 断路器自动复位: {task_name}")
                return False
        except Exception:
            pass
    return True


def _record_circuit_result(db: sqlite3.Connection, task_name: str, success: bool):
    """Update circuit breaker state after task execution"""
    now = datetime.now().isoformat()
    if success:
        db.execute(
            "INSERT INTO circuit_breakers (task_name, consecutive_failures, last_failure, tripped) "
            "VALUES (?, 0, NULL, 0) "
            "ON CONFLICT(task_name) DO UPDATE SET consecutive_failures=0, tripped=0",
            (task_name,)
        )
    else:
        db.execute(
            "INSERT INTO circuit_breakers (task_name, consecutive_failures, last_failure, tripped) "
            "VALUES (?, 1, ?, 0) "
            "ON CONFLICT(task_name) DO UPDATE SET "
            "consecutive_failures=consecutive_failures+1, last_failure=?",
            (task_name, now, now)
        )
        db.commit()
        # Check if should trip
        row = db.execute(
            "SELECT consecutive_failures FROM circuit_breakers WHERE task_name=?", (task_name,)
        ).fetchone()
        if row and row[0] >= CIRCUIT_BREAKER_THRESHOLD:
            db.execute(
                "UPDATE circuit_breakers SET tripped=1, tripped_at=? WHERE task_name=?",
                (now, task_name)
            )
            _log(f"    ⚠️ 断路器触发: {task_name} (连续{row[0]}次失败)")
    db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 统一任务执行器 (with retry + circuit breaker)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _execute_task(db: sqlite3.Connection, mode: str, task_def: dict) -> dict:
    """Execute a single task with retry and circuit breaker logic"""
    name = task_def["name"]
    script = task_def["script"]
    args = task_def.get("args", [])
    timeout = task_def.get("timeout", 120)
    max_retries = task_def.get("retry", 0)

    # Circuit breaker check
    if _is_circuit_tripped(db, name):
        _log(f"  ⚡ {name}: 断路器已触发, 跳过")
        _record(db, mode, name, "circuit_open", "circuit breaker tripped", 0)
        return {"name": name, "ok": False, "ms": 0, "status": "circuit_open", "retries": 0}

    # Execute with retries
    attempt = 0
    result = None
    while attempt <= max_retries:
        if attempt > 0:
            _log(f"    ↻ 重试 {attempt}/{max_retries}: {name}")
            time.sleep(min(attempt * 2, 10))  # backoff
        result = _run_v15(script, args, timeout)
        if result["ok"]:
            break
        attempt += 1

    ok = result["ok"] if result else False
    status = "ok" if ok else "fail"
    _record(db, mode, name, status, (result["output"] if result else "")[:500],
            result["duration_ms"] if result else 0, attempt)
    _record_circuit_result(db, name, ok)

    icon = "✅" if ok else "❌"
    retry_info = f" (retry={attempt})" if attempt > 0 else ""
    _log(f"  {icon} {name}: {result['duration_ms'] if result else 0}ms{retry_info}")

    return {"name": name, "ok": ok, "ms": result["duration_ms"] if result else 0,
            "status": status, "retries": attempt}


def _run_mode(mode: str) -> dict:
    """Generic mode runner using schedule registry"""
    tasks_defs = SCHEDULE_REGISTRY.get(mode, [])
    if not tasks_defs:
        return {"mode": mode, "error": f"No tasks registered for mode '{mode}'", "tasks": []}

    _log(f"═══ {mode.upper()} 开始 ═══")
    db = _get_db()
    total_start = time.time()
    tasks_results = []

    for task_def in tasks_defs:
        _log(f"  ▶ {task_def['name']} ({task_def['script']})")
        r = _execute_task(db, mode, task_def)
        tasks_results.append(r)

    total_ms = int((time.time() - total_start) * 1000)
    ok_count = sum(1 for t in tasks_results if t["ok"])
    _log(f"═══ {mode.upper()} 完成: {ok_count}/{len(tasks_results)} 成功, 总耗时 {total_ms}ms ═══")
    return {"mode": mode, "tasks": tasks_results, "total_ms": total_ms}


def run_daily():
    return _run_mode("daily")


def run_tick():
    return _run_mode("tick")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# --health: 健康检查 (合并3个Cron)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_health():
    """合并: registry任务 + 脚本完整性 + 磁盘 + DB巡检 + 自愈"""
    _log("🏥 HEALTH 检查开始")
    db = _get_db()
    total_start = time.time()
    tasks_results = []
    issues = []

    # Run registered health tasks
    for task_def in SCHEDULE_REGISTRY["health"]:
        _log(f"  ▶ {task_def['name']} ({task_def['script']})")
        r = _execute_task(db, "health", task_def)
        tasks_results.append(r)
        if not r["ok"] and task_def.get("critical"):
            issues.append(f"{task_def['name']} 异常")

    # Extra checks: script integrity
    _log("  ▶ 脚本完整性")
    expected = [
        "llm-router-v15.py", "cluster-client-v15.py", "prompt-cache-v15.py",
        "memory-fabric-v15.py", "trajectory-recorder-v15.py", "learning-loop-v15.py",
        "skill-forge-v15.py", "self-calibration-v15.py", "rule-miner-v15.py",
        "rule-engine-v15.py", "sense-bus-v15.py", "version.py",
    ]
    missing = [f for f in expected if not (V15_DIR / f).exists()]
    scripts_ok = len(missing) == 0
    tasks_results.append({"name": "脚本完整性", "ok": scripts_ok, "ms": 0, "missing": missing})
    if missing:
        issues.append(f"缺失脚本: {missing}")
    _record(db, "health", "脚本完整性", "ok" if scripts_ok else "fail", str(missing), 0)

    # Disk space
    _log("  ▶ 磁盘空间")
    try:
        st = os.statvfs(str(WORKSPACE))
        free_gb = round((st.f_bavail * st.f_frsize) / (1024 ** 3), 1)
        disk_ok = free_gb > 5.0
        tasks_results.append({"name": "磁盘空间", "ok": disk_ok, "ms": 0, "free_gb": free_gb})
        if not disk_ok:
            issues.append(f"磁盘空间不足: {free_gb}GB")
        _record(db, "health", "磁盘空间", "ok" if disk_ok else "warn", f"{free_gb}GB", 0)
    except Exception:
        tasks_results.append({"name": "磁盘空间", "ok": True, "ms": 0})

    # DB sizes
    _log("  ▶ 数据库巡检")
    for db_file in STATE_DIR.glob("*.db"):
        size_mb = round(db_file.stat().st_size / 1024 / 1024, 1)
        if size_mb > 500:
            issues.append(f"数据库过大: {db_file.name} = {size_mb}MB")
            _try_self_heal(db, "oversized_db", db_file.name)

    # Self-heal: daemon log size
    if DAEMON_LOG.exists() and DAEMON_LOG.stat().st_size > 10 * 1024 * 1024:
        _try_self_heal(db, "stale_log", str(DAEMON_LOG))

    total_ms = int((time.time() - total_start) * 1000)
    ok_count = sum(1 for t in tasks_results if t["ok"])
    status = "healthy" if not issues else "degraded"

    _log(f"🏥 HEALTH 完成: {ok_count}/{len(tasks_results)} 通过, {len(issues)} 问题, {total_ms}ms")
    for issue in issues:
        _log(f"  ⚠️  {issue}")

    return {"mode": "health", "status": status, "tasks": tasks_results,
            "issues": issues, "total_ms": total_ms}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Self-Heal Actions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _try_self_heal(db: sqlite3.Connection, action_key: str, target: str):
    """Attempt a self-heal action and log the result"""
    action_info = SELF_HEAL_ACTIONS.get(action_key)
    if not action_info:
        return

    result_text = ""
    try:
        if action_key == "oversized_db":
            db_path = STATE_DIR / target
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                # Delete old records (>60 days)
                for table in ["runs", "events", "diagnostics"]:
                    try:
                        conn.execute(f"DELETE FROM {table} WHERE created_at < datetime('now', '-60 days')")
                    except Exception:
                        pass
                conn.execute("VACUUM")
                conn.commit()
                conn.close()
                result_text = f"cleaned {target}"

        elif action_key == "stale_log":
            if Path(target).exists():
                # Keep last 1000 lines
                lines = Path(target).read_text(encoding="utf-8", errors="ignore").splitlines()
                if len(lines) > 1000:
                    Path(target).write_text("\n".join(lines[-1000:]) + "\n", encoding="utf-8")
                    result_text = f"truncated to 1000 lines"

        elif action_key == "missing_state_dir":
            os.makedirs(STATE_DIR, exist_ok=True)
            result_text = "recreated state dir"

        elif action_key == "stale_db":
            db_path = STATE_DIR / target
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                conn.execute("VACUUM")
                conn.close()
                result_text = f"vacuumed {target}"

        _log(f"    🔧 自愈: {action_key} on {target} → {result_text}")

    except Exception as e:
        result_text = f"error: {str(e)[:200]}"
        _log(f"    ❌ 自愈失败: {action_key} on {target}: {e}")

    try:
        db.execute(
            "INSERT INTO self_heal_log (action, target, result) VALUES (?, ?, ?)",
            (action_key, target, result_text)
        )
        db.commit()
    except Exception:
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# --status: 运行历史
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def show_status():
    db = _get_db()
    print("📊 Daemon Loop V15 控制面板")
    print("=" * 60)

    # 最近运行概览
    print("\n🟢 最近运行:")
    for mode in ["daily", "tick", "health"]:
        cursor = db.execute(
            "SELECT created_at, status, duration_ms FROM runs WHERE mode=? ORDER BY created_at DESC LIMIT 1",
            (mode,)
        )
        row = cursor.fetchone()
        if row:
            icon = "✅" if row[1] == "ok" else "❌"
            print(f"  {icon} --{mode}: 最近 {row[0]}, {row[1]}, {row[2]}ms")
        else:
            print(f"  ⏳ --{mode}: 从未运行")

    # 统计
    cursor = db.execute(
        "SELECT mode, COUNT(*), SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END), AVG(duration_ms) "
        "FROM runs GROUP BY mode"
    )
    print("\n📊 历史统计:")
    for row in cursor.fetchall():
        mode, total, ok, avg_ms = row
        print(f"    --{mode}: {total}次, {ok}成功, 平均{int(avg_ms or 0)}ms")

    # Circuit breakers
    print("\n⚡ 断路器状态:")
    rows = db.execute(
        "SELECT task_name, consecutive_failures, tripped, tripped_at, last_failure FROM circuit_breakers ORDER BY task_name"
    ).fetchall()
    if rows:
        for row in rows:
            icon = "🟥" if row[2] else "🟩"
            info = f"failures={row[1]}"
            if row[2]:
                info += f", tripped_at={row[3]}"
            print(f"  {icon} {row[0]:25s} {info}")
    else:
        print("  ✅ 无断路器记录")

    # Self-heal log
    print("\n🔧 最近自愈:")
    heal_rows = db.execute(
        "SELECT action, target, result, created_at FROM self_heal_log ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    if heal_rows:
        for row in heal_rows:
            print(f"  [{row[3]}] {row[0]} on {row[1]} → {row[2][:60]}")
    else:
        print("  无自愈记录")

    # 最近失败
    cursor = db.execute(
        "SELECT created_at, mode, task, message FROM runs WHERE status='fail' ORDER BY created_at DESC LIMIT 5"
    )
    fails = cursor.fetchall()
    if fails:
        print(f"\n❌ 最近失败 ({len(fails)}):")
        for row in fails:
            print(f"    [{row[0]}] {row[1]}/{row[2]}: {row[3][:80]}")

    # Schedule registry summary
    print(f"\n📋 调度注册表:")
    for mode, tasks in SCHEDULE_REGISTRY.items():
        names = [t['name'] for t in tasks]
        print(f"  --{mode} ({len(tasks)}个): {', '.join(names)}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    if "--daily" in sys.argv:
        result = run_daily()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--tick" in sys.argv:
        result = run_tick()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--health" in sys.argv:
        result = run_health()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--status" in sys.argv:
        show_status()

    elif "--registry" in sys.argv:
        print("📋 Schedule Registry:")
        for mode, tasks in SCHEDULE_REGISTRY.items():
            print(f"\n  --{mode}:")
            for t in tasks:
                retry = f"retry={t.get('retry', 0)}" if t.get('retry') else ""
                crit = " [CRITICAL]" if t.get('critical') else ""
                print(f"    {t['name']:20s} {t['script']:35s} timeout={t['timeout']}s {retry}{crit}")

    elif "--heal-log" in sys.argv:
        db = _get_db()
        rows = db.execute(
            "SELECT action, target, result, created_at FROM self_heal_log ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        print(f"🔧 Self-Heal Log ({len(rows)} 条):")
        for row in rows:
            print(f"  [{row[3]}] {row[0]} on {row[1]} → {row[2][:80]}")

    elif "--breakers" in sys.argv:
        db = _get_db()
        rows = db.execute(
            "SELECT task_name, consecutive_failures, tripped, tripped_at, last_failure FROM circuit_breakers ORDER BY task_name"
        ).fetchall()
        print(f"⚡ Circuit Breakers ({len(rows)}):")
        for row in rows:
            icon = "🟥" if row[2] else "🟩"
            print(f"  {icon} {row[0]:25s} failures={row[1]}, tripped={bool(row[2])}, last={row[4] or 'never'}")

    else:
        print("V15 Daemon Loop — 永驻循环控制器")
        print("  --daily      每日任务")
        print("  --tick       心跳")
        print("  --health     健康检查 + 自愈")
        print("  --status     控制面板")
        print("  --registry   调度注册表")
        print("  --breakers   断路器状态")
        print("  --heal-log   自愈日志")
