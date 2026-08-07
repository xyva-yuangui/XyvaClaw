#!/usr/bin/env python3
"""
V15 轨迹记录器 — 记录每次消息处理的完整轨迹用于事后学习
替代 v7-kernel-log.db 的简单日志，增加路由决策、延迟分解、质量评分

用法:
  recorder = TrajectoryRecorder()
  recorder.record(result_dict)
  stats = recorder.get_stats(days=7)
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
TRAJECTORY_DB = STATE_DIR / "v15-trajectory.db"


class TrajectoryRecorder:
    def __init__(self):
        self._conn = None

    def _get_db(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._conn = sqlite3.connect(str(TRAJECTORY_DB))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                session_id TEXT,
                user_input TEXT,
                intent TEXT,
                action_type TEXT,
                complexity TEXT,
                source TEXT,
                route_rule TEXT,
                model_used TEXT,
                total_ms INTEGER,
                classify_ms INTEGER DEFAULT 0,
                route_ms INTEGER DEFAULT 0,
                llm_ms INTEGER DEFAULT 0,
                memory_ms INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 0,
                has_reasoning INTEGER DEFAULT 0,
                has_memory INTEGER DEFAULT 0,
                error TEXT DEFAULT '',
                data TEXT
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_traj_ts ON trajectories(ts)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_traj_intent ON trajectories(intent)")
        return self._conn

    def record(self, result: dict):
        """记录一条处理轨迹"""
        conn = self._get_db()
        intent_info = result.get("intent", {})
        routing = result.get("routing", {})
        try:
            conn.execute("""
                INSERT INTO trajectories
                (ts, session_id, user_input, intent, action_type, complexity, source,
                 route_rule, model_used, total_ms, classify_ms, route_ms, llm_ms, memory_ms,
                 quality_score, has_reasoning, has_memory, error, data)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                datetime.now().isoformat(),
                result.get("session_id", ""),
                (result.get("user_input", "") or "")[:200],
                intent_info.get("primary", "") if isinstance(intent_info, dict) else str(intent_info),
                result.get("action_type", ""),
                intent_info.get("complexity", "") if isinstance(intent_info, dict) else "",
                result.get("_source", ""),
                routing.get("route_rule", result.get("_route_rule", "")),
                routing.get("suggested_model", routing.get("model_used", "")),
                result.get("total_ms", 0),
                result.get("_classify_ms", 0),
                result.get("_route_ms", 0),
                result.get("_llm_ms", 0),
                result.get("_memory_ms", 0),
                result.get("_quality_score", 0),
                1 if result.get("reasoning_chain") or result.get("reasoning_required") else 0,
                1 if result.get("memory_hits") or result.get("has_memory") else 0,
                result.get("error", ""),
                json.dumps(result, ensure_ascii=False, default=str)[:5000],
            ))
            conn.commit()
        except Exception:
            pass

    def get_stats(self, days: int = 7) -> dict:
        """获取近N天统计"""
        conn = self._get_db()
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        total = conn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ?", (cutoff,)).fetchone()[0]
        avg_ms = conn.execute("SELECT AVG(total_ms) FROM trajectories WHERE ts > ? AND total_ms > 0", (cutoff,)).fetchone()[0] or 0
        p50 = conn.execute("SELECT total_ms FROM trajectories WHERE ts > ? AND total_ms > 0 ORDER BY total_ms LIMIT 1 OFFSET ?",
                           (cutoff, max(0, total // 2))).fetchone()
        by_intent = conn.execute("""
            SELECT intent, COUNT(*), AVG(total_ms) FROM trajectories
            WHERE ts > ? GROUP BY intent ORDER BY COUNT(*) DESC LIMIT 10
        """, (cutoff,)).fetchall()
        by_source = conn.execute("""
            SELECT source, COUNT(*) FROM trajectories
            WHERE ts > ? GROUP BY source ORDER BY COUNT(*) DESC
        """, (cutoff,)).fetchall()
        errors = conn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ? AND error != ''", (cutoff,)).fetchone()[0]

        return {
            "period_days": days,
            "total_requests": total,
            "avg_latency_ms": round(avg_ms),
            "p50_latency_ms": p50[0] if p50 else 0,
            "error_count": errors,
            "by_intent": [(i, c, round(a)) for i, c, a in by_intent],
            "by_source": dict(by_source),
        }


_recorder = None

def get_recorder() -> TrajectoryRecorder:
    global _recorder
    if _recorder is None:
        _recorder = TrajectoryRecorder()
    return _recorder


if __name__ == "__main__":
    rec = get_recorder()
    if "--stats" in sys.argv:
        days = 7
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else 7
        stats = rec.get_stats(days)
        print(f"📊 Trajectory Stats (last {stats['period_days']} days)")
        print(f"  Total: {stats['total_requests']}")
        print(f"  Avg latency: {stats['avg_latency_ms']}ms")
        print(f"  P50 latency: {stats['p50_latency_ms']}ms")
        print(f"  Errors: {stats['error_count']}")
        if stats['by_intent']:
            print(f"\n  Top intents:")
            for intent, count, avg in stats['by_intent']:
                print(f"    {count:4d}  {intent:30s}  avg {avg}ms")
        if stats['by_source']:
            print(f"\n  By source:")
            for src, cnt in stats['by_source'].items():
                print(f"    {cnt:4d}  {src}")
    else:
        print("V15 Trajectory Recorder")
        print("  --stats [--days N]  查看统计")
