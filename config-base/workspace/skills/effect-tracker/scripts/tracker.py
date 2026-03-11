#!/usr/bin/env python3
"""
Effect Tracker — Unified skill execution metrics collection and reporting.
Supports: record, today, report, failures, --check.
"""

import argparse
import contextlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = os.path.expanduser("~/.openclaw/logs/effect-tracker.sqlite")
DAILY_LOG_DIR = os.path.expanduser("~/.openclaw/logs/daily")


# ── database ────────────────────────────────────────────────────────────────

def get_db(db_path: str = DEFAULT_DB) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS skill_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            action TEXT,
            status TEXT NOT NULL CHECK(status IN ('ok','warn','fail')),
            latency_ms INTEGER,
            tokens_used INTEGER DEFAULT 0,
            api_calls INTEGER DEFAULT 0,
            error_type TEXT,
            error_message TEXT,
            metadata TEXT DEFAULT '{}'
        );
        CREATE INDEX IF NOT EXISTS idx_events_skill ON skill_events(skill_name);
        CREATE INDEX IF NOT EXISTS idx_events_ts ON skill_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_status ON skill_events(status);

        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            invocations INTEGER DEFAULT 0,
            successes INTEGER DEFAULT 0,
            failures INTEGER DEFAULT 0,
            avg_latency_ms REAL,
            p95_latency_ms REAL,
            total_tokens INTEGER DEFAULT 0,
            total_api_calls INTEGER DEFAULT 0,
            business_metrics TEXT DEFAULT '{}',
            PRIMARY KEY (date, skill_name)
        );
    """)
    conn.commit()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── record event ────────────────────────────────────────────────────────────

def record_event(conn, skill_name: str, action: str = None, status: str = "ok",
                 latency_ms: int = None, tokens_used: int = 0, api_calls: int = 0,
                 error_type: str = None, error_message: str = None, metadata: dict = None):
    ts = _now()
    conn.execute("""
        INSERT INTO skill_events
        (timestamp, skill_name, action, status, latency_ms, tokens_used, api_calls,
         error_type, error_message, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (ts, skill_name, action, status, latency_ms, tokens_used, api_calls,
          error_type, error_message, json.dumps(metadata or {}, ensure_ascii=False)))
    conn.commit()

    # Also append to daily JSONL
    _append_daily_log(ts, skill_name, action, status, latency_ms, error_type)
    return ts


def _append_daily_log(ts, skill, action, status, latency_ms, error_type):
    os.makedirs(DAILY_LOG_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    logfile = os.path.join(DAILY_LOG_DIR, f"{date_str}.jsonl")
    entry = {
        "ts": ts, "skill": skill, "action": action,
        "status": status, "latency_ms": latency_ms, "error_type": error_type,
    }
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Python decorator / context manager ──────────────────────────────────────

@contextlib.contextmanager
def track(skill_name: str, action: str = None, db_path: str = DEFAULT_DB):
    """Context manager for tracking skill execution."""
    conn = get_db(db_path)
    meta = {}
    start = time.monotonic()
    status = "ok"
    err_type = err_msg = None
    try:
        class _Tracker:
            def set_metadata(self, d: dict):
                meta.update(d)
        yield _Tracker()
    except Exception as e:
        status = "fail"
        err_type = type(e).__name__
        err_msg = str(e)[:500]
        raise
    finally:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        record_event(conn, skill_name, action, status, elapsed_ms,
                     error_type=err_type, error_message=err_msg, metadata=meta)
        conn.close()


# ── queries ─────────────────────────────────────────────────────────────────

def today_summary(conn) -> dict:
    date = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT skill_name,
               COUNT(*) as invocations,
               SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) as successes,
               SUM(CASE WHEN status='fail' THEN 1 ELSE 0 END) as failures,
               ROUND(AVG(latency_ms)) as avg_latency_ms,
               SUM(tokens_used) as total_tokens,
               SUM(api_calls) as total_api_calls
        FROM skill_events
        WHERE timestamp LIKE ?
        GROUP BY skill_name
        ORDER BY invocations DESC
    """, (f"{date}%",)).fetchall()

    total = {"invocations": 0, "successes": 0, "failures": 0}
    skills = []
    for r in rows:
        d = dict(r)
        d["success_rate"] = round(d["successes"] / d["invocations"] * 100, 1) if d["invocations"] else 0
        skills.append(d)
        total["invocations"] += d["invocations"]
        total["successes"] += d["successes"]
        total["failures"] += d["failures"]

    total["success_rate"] = round(total["successes"] / total["invocations"] * 100, 1) if total["invocations"] else 0
    return {"date": date, "total": total, "skills": skills}


def skill_report(conn, skill_name: str, days: int = 7) -> dict:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT DATE(timestamp) as date,
               COUNT(*) as invocations,
               SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) as successes,
               SUM(CASE WHEN status='fail' THEN 1 ELSE 0 END) as failures,
               ROUND(AVG(latency_ms)) as avg_latency_ms
        FROM skill_events
        WHERE skill_name=? AND timestamp >= ?
        GROUP BY DATE(timestamp)
        ORDER BY date
    """, (skill_name, since)).fetchall()
    return {"skill": skill_name, "days": days, "daily": [dict(r) for r in rows]}


def weekly_report(conn) -> dict:
    since = (datetime.now() - timedelta(days=7)).isoformat()

    total_row = conn.execute("""
        SELECT COUNT(*) as invocations,
               SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) as successes,
               SUM(CASE WHEN status='fail' THEN 1 ELSE 0 END) as failures,
               ROUND(AVG(latency_ms)) as avg_latency_ms,
               SUM(tokens_used) as total_tokens
        FROM skill_events WHERE timestamp >= ?
    """, (since,)).fetchone()

    top_skills = conn.execute("""
        SELECT skill_name,
               COUNT(*) as invocations,
               ROUND(SUM(CASE WHEN status='ok' THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) as success_rate,
               ROUND(AVG(latency_ms)) as avg_latency_ms
        FROM skill_events WHERE timestamp >= ?
        GROUP BY skill_name ORDER BY invocations DESC LIMIT 10
    """, (since,)).fetchall()

    failures = conn.execute("""
        SELECT error_type, COUNT(*) as cnt, skill_name
        FROM skill_events
        WHERE timestamp >= ? AND status='fail' AND error_type IS NOT NULL
        GROUP BY error_type, skill_name ORDER BY cnt DESC LIMIT 10
    """, (since,)).fetchall()

    t = dict(total_row) if total_row else {}
    t["success_rate"] = round(t.get("successes", 0) / t["invocations"] * 100, 1) if t.get("invocations") else 0

    return {
        "period": f"{(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
        "total": t,
        "top_skills": [dict(r) for r in top_skills],
        "failure_hotspots": [dict(r) for r in failures],
    }


def failure_analysis(conn, days: int = 30, top: int = 10) -> list:
    since = (datetime.now() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT skill_name, error_type, error_message, COUNT(*) as cnt,
               MAX(timestamp) as last_seen
        FROM skill_events
        WHERE timestamp >= ? AND status='fail'
        GROUP BY skill_name, error_type
        ORDER BY cnt DESC LIMIT ?
    """, (since, top)).fetchall()
    return [dict(r) for r in rows]


# ── build daily summary ─────────────────────────────────────────────────────

def build_daily_summary(conn, date: str = None):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    rows = conn.execute("""
        SELECT skill_name,
               COUNT(*) as invocations,
               SUM(CASE WHEN status='ok' THEN 1 ELSE 0 END) as successes,
               SUM(CASE WHEN status='fail' THEN 1 ELSE 0 END) as failures,
               ROUND(AVG(latency_ms)) as avg_latency_ms,
               SUM(tokens_used) as total_tokens,
               SUM(api_calls) as total_api_calls
        FROM skill_events
        WHERE timestamp LIKE ?
        GROUP BY skill_name
    """, (f"{date}%",)).fetchall()

    # Compute p95 per skill
    for r in rows:
        latencies = conn.execute("""
            SELECT latency_ms FROM skill_events
            WHERE timestamp LIKE ? AND skill_name=? AND latency_ms IS NOT NULL
            ORDER BY latency_ms
        """, (f"{date}%", r["skill_name"])).fetchall()
        p95 = None
        if latencies:
            idx = int(len(latencies) * 0.95)
            p95 = latencies[min(idx, len(latencies) - 1)]["latency_ms"]

        conn.execute("""
            INSERT OR REPLACE INTO daily_summary
            (date, skill_name, invocations, successes, failures, avg_latency_ms, p95_latency_ms,
             total_tokens, total_api_calls)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, r["skill_name"], r["invocations"], r["successes"], r["failures"],
              r["avg_latency_ms"], p95, r["total_tokens"], r["total_api_calls"]))

    conn.commit()
    return len(rows)


# ── health check ────────────────────────────────────────────────────────────

def health_check(db_path: str = DEFAULT_DB) -> dict:
    checks = []
    try:
        conn = get_db(db_path)
        conn.execute("SELECT 1")
        checks.append({"name": "sqlite_db", "type": "file", "status": "ok", "path": db_path})

        cnt = conn.execute("SELECT COUNT(*) FROM skill_events").fetchone()[0]
        checks.append({"name": "event_count", "type": "env", "status": "ok", "message": f"{cnt} events"})

        latest = conn.execute("SELECT MAX(timestamp) FROM skill_events").fetchone()[0]
        if latest:
            age_hours = (datetime.now() - datetime.fromisoformat(latest)).total_seconds() / 3600
            status = "ok" if age_hours < 24 else "warn"
            checks.append({"name": "latest_event", "type": "env", "status": status,
                           "message": f"Last event: {latest} ({age_hours:.1f}h ago)"})

        # Check daily log dir
        if os.path.isdir(DAILY_LOG_DIR):
            checks.append({"name": "daily_log_dir", "type": "file", "status": "ok", "path": DAILY_LOG_DIR})
        else:
            checks.append({"name": "daily_log_dir", "type": "file", "status": "warn",
                           "message": "Daily log dir does not exist yet"})

        conn.close()
    except Exception as e:
        checks.append({"name": "sqlite_db", "type": "file", "status": "fail", "message": str(e)})

    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {
        "skill": "effect-tracker", "version": "1.0.0",
        "status": overall, "checks": checks, "timestamp": _now(),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Effect Tracker CLI")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--check", action="store_true", help="Health check")

    sub = parser.add_subparsers(dest="command")

    # record
    p_rec = sub.add_parser("record", help="Record a skill event")
    p_rec.add_argument("--skill", required=True)
    p_rec.add_argument("--action")
    p_rec.add_argument("--status", default="ok", choices=["ok", "warn", "fail"])
    p_rec.add_argument("--latency-ms", type=int)
    p_rec.add_argument("--tokens", type=int, default=0)
    p_rec.add_argument("--api-calls", type=int, default=0)
    p_rec.add_argument("--error-type")
    p_rec.add_argument("--error-message")

    # today
    sub.add_parser("today", help="Today's summary")

    # skill report
    p_skill = sub.add_parser("skill", help="Report for specific skill")
    p_skill.add_argument("--name", required=True)
    p_skill.add_argument("--days", type=int, default=7)

    # report
    p_report = sub.add_parser("report", help="Weekly report")
    p_report.add_argument("--period", default="weekly", choices=["weekly"])

    # failures
    p_fail = sub.add_parser("failures", help="Failure analysis")
    p_fail.add_argument("--days", type=int, default=30)
    p_fail.add_argument("--top", type=int, default=10)

    # build-summary
    p_sum = sub.add_parser("build-summary", help="Build daily summary")
    p_sum.add_argument("--date")

    args = parser.parse_args()

    if args.check:
        result = health_check(args.db)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    conn = get_db(args.db)

    if args.command == "record":
        ts = record_event(conn, args.skill, args.action, args.status,
                          args.latency_ms, args.tokens, args.api_calls,
                          args.error_type, args.error_message)
        print(json.dumps({"recorded": True, "timestamp": ts}))

    elif args.command == "today":
        print(json.dumps(today_summary(conn), indent=2, ensure_ascii=False))

    elif args.command == "skill":
        print(json.dumps(skill_report(conn, args.name, args.days), indent=2, ensure_ascii=False))

    elif args.command == "report":
        print(json.dumps(weekly_report(conn), indent=2, ensure_ascii=False))

    elif args.command == "failures":
        print(json.dumps(failure_analysis(conn, args.days, args.top), indent=2, ensure_ascii=False))

    elif args.command == "build-summary":
        cnt = build_daily_summary(conn, args.date)
        print(json.dumps({"date": args.date or datetime.now().strftime("%Y-%m-%d"), "skills_summarized": cnt}))

    conn.close()


if __name__ == "__main__":
    main()
