#!/usr/bin/env python3
"""
V15 先知引擎 — 预判需求 + 上下文预取 + 主动发现 + 预生成缓存
升级自: curiosity-engine-v12.py

四大功能:
  1. 时间模式识别: 按历史行为预判用户需要什么
  2. 上下文预取: 检测当前活动, 预加载相关数据
  3. 主动发现: 扫描异动/更新/成本, 主动推送
  4. 预生成缓存: 高频查询提前缓存

关键: 只用本地 mini2 后脑, 零云端成本

CLI:
  python3 scripts/v15/prescience-v15.py --scan       # 全量扫描
  python3 scripts/v15/prescience-v15.py --patterns    # 查看时间模式
  python3 scripts/v15/prescience-v15.py --prefetch    # 执行预取
  python3 scripts/v15/prescience-v15.py --discoveries  # 查看主动发现
  python3 scripts/v15/prescience-v15.py --status      # 状态
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
PRESCIENCE_DB = STATE_DIR / "v15-prescience.db"
TRAJECTORY_DB = STATE_DIR / "v15-trajectory.db"
ROUTING_LOG_DB = STATE_DIR / "v15-routing-log.db"
SENSE_BUS_DB = STATE_DIR / "v15-sense-bus.db"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据库
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Discovery lifecycle stages
DISCOVERY_LIFECYCLE = ["new", "acknowledged", "investigating", "resolved", "archived"]
DISCOVERY_TRANSITIONS = {
    "new": ["acknowledged", "archived"],
    "acknowledged": ["investigating", "resolved", "archived"],
    "investigating": ["resolved", "archived"],
    "resolved": ["archived"],
    "archived": [],
}


def _get_db() -> sqlite3.Connection:
    os.makedirs(STATE_DIR, exist_ok=True)
    db = sqlite3.connect(str(PRESCIENCE_DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT,
            description TEXT,
            hour INTEGER,
            day_of_week INTEGER,
            frequency INTEGER DEFAULT 1,
            last_seen TEXT,
            action TEXT,
            confidence REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS discoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discovery_type TEXT,
            title TEXT,
            detail TEXT,
            priority INTEGER DEFAULT 1,
            status TEXT DEFAULT 'new',
            resolved_at TEXT,
            resolution_note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS prefetch_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            cache_key TEXT,
            status TEXT,
            latency_ms INTEGER,
            hit INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS quality_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_type TEXT,
            value REAL,
            detail TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # Migrations
    for col, typedef in [("resolved_at", "TEXT"), ("resolution_note", "TEXT DEFAULT ''")]:
        try:
            db.execute(f"ALTER TABLE discoveries ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    for col, typedef in [("hit", "INTEGER DEFAULT 0")]:
        try:
            db.execute(f"ALTER TABLE prefetch_log ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    db.commit()
    return db


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 先知引擎核心
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PrescienceEngine:
    def __init__(self):
        self._db = _get_db()

    def _pattern_exists(self, pattern_type: str, description: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM patterns WHERE pattern_type=? AND description=? LIMIT 1",
            (pattern_type, description),
        ).fetchone()
        return bool(row)

    def _discovery_exists(self, discovery_type: str, title: str) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM discoveries WHERE discovery_type=? AND title=? AND created_at > datetime('now', '-1 day') LIMIT 1",
            (discovery_type, title),
        ).fetchone()
        return bool(row)

    # ── 1. 时间模式识别 ──

    def analyze_time_patterns(self) -> list:
        """分析用户行为的时间模式"""
        patterns = []

        # 从轨迹数据库提取时间分布
        if TRAJECTORY_DB.exists():
            try:
                tdb = sqlite3.connect(str(TRAJECTORY_DB))
                cursor = tdb.execute("""
                    SELECT
                        CAST(strftime('%H', created_at) AS INTEGER) as hour,
                        CAST(strftime('%w', created_at) AS INTEGER) as dow,
                        COUNT(*) as cnt
                    FROM trajectories
                    WHERE created_at > datetime('now', '-30 days')
                    GROUP BY hour, dow
                    ORDER BY cnt DESC
                    LIMIT 20
                """)
                for row in cursor.fetchall():
                    hour, dow, count = row
                    if count >= 3:
                        patterns.append({
                            "type": "active_period",
                            "hour": hour, "day_of_week": dow,
                            "frequency": count,
                            "confidence": min(count / 30, 1.0),
                        })
                tdb.close()
            except Exception:
                pass

        # 从路由日志提取高频意图
        if ROUTING_LOG_DB.exists():
            try:
                rdb = sqlite3.connect(str(ROUTING_LOG_DB))
                cursor = rdb.execute("""
                    SELECT rule_id, COUNT(*) as cnt
                    FROM routing_log
                    WHERE created_at > datetime('now', '-7 days')
                    GROUP BY rule_id
                    HAVING cnt >= 3
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                for row in cursor.fetchall():
                    rule_id, count = row
                    patterns.append({
                        "type": "frequent_intent",
                        "rule_id": rule_id,
                        "frequency": count,
                        "confidence": min(count / 20, 1.0),
                    })
                rdb.close()
            except Exception:
                pass

        # 持久化模式
        for p in patterns:
            desc = json.dumps(p, ensure_ascii=False)
            if self._pattern_exists(p["type"], desc):
                continue
            self._db.execute(
                "INSERT INTO patterns (pattern_type, description, hour, day_of_week, frequency, "
                "last_seen, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["type"], desc,
                 p.get("hour", -1), p.get("day_of_week", -1),
                 p.get("frequency", 1), datetime.now().isoformat(),
                 p.get("confidence", 0.5))
            )
        self._db.commit()
        return patterns

    # ── 2. 上下文预取 ──

    def prefetch(self) -> list:
        """根据时间模式预取数据"""
        results = []
        now = datetime.now()
        current_hour = now.hour
        current_dow = now.weekday()  # 0=Monday

        # 检查是否有匹配当前时间的模式
        cursor = self._db.execute(
            "SELECT description, action, confidence FROM patterns "
            "WHERE (hour = ? OR hour = ?) AND confidence >= 0.6 "
            "ORDER BY confidence DESC LIMIT 5",
            (current_hour, (current_hour + 1) % 24)
        )

        for row in cursor.fetchall():
            desc, action, confidence = row
            results.append({
                "pattern": desc,
                "action": action or "no_action",
                "confidence": confidence,
                "status": "ready",
            })

        # 工作日早上: 准备今日摘要
        if current_dow < 5 and 8 <= current_hour <= 9:
            results.append({
                "pattern": "工作日早间准备",
                "action": "prepare_daily_summary",
                "confidence": 0.8,
                "status": "suggested",
            })

        # 周一: 可能关注股市
        if current_dow == 0 and 8 <= current_hour <= 10:
            results.append({
                "pattern": "周一A股关注",
                "action": "prefetch_stock_data",
                "confidence": 0.7,
                "status": "suggested",
            })

        # 月初: 系统健康报告
        if now.day <= 3:
            results.append({
                "pattern": "月初系统审计",
                "action": "prepare_health_report",
                "confidence": 0.75,
                "status": "suggested",
            })

        for item in results:
            cache_key = f"{item['action']}::{current_hour}::{current_dow}"
            self._db.execute(
                "INSERT INTO prefetch_log (query, cache_key, status, latency_ms) VALUES (?, ?, ?, ?)",
                (item["pattern"], cache_key, item.get("status", "ready"), 0),
            )
            item["cache_key"] = cache_key
        self._db.commit()

        return results

    # ── 3. 主动发现 ──

    def discover(self) -> list:
        """扫描异动, 生成主动发现"""
        discoveries = []

        # 3a. 数据库大小异动
        for db_file in STATE_DIR.glob("*.db"):
            size_mb = db_file.stat().st_size / 1024 / 1024
            if size_mb > 200:
                discoveries.append({
                    "type": "db_growth",
                    "title": f"数据库 {db_file.name} 已达 {size_mb:.0f}MB",
                    "priority": 2 if size_mb < 500 else 1,
                })

        # 3b. 路由异常检测 (连续失败)
        if ROUTING_LOG_DB.exists():
            try:
                rdb = sqlite3.connect(str(ROUTING_LOG_DB))
                cursor = rdb.execute("""
                    SELECT model_used, COUNT(*) as fail_cnt
                    FROM routing_log
                    WHERE status != 'ok' AND created_at > datetime('now', '-1 day')
                    GROUP BY model_used
                    HAVING fail_cnt >= 3
                """)
                for row in cursor.fetchall():
                    model, fail_cnt = row
                    discoveries.append({
                        "type": "routing_anomaly",
                        "title": f"模型 {model} 24h内失败 {fail_cnt} 次",
                        "priority": 1,
                    })
                rdb.close()
            except Exception:
                pass

        if SENSE_BUS_DB.exists():
            try:
                sdb = sqlite3.connect(str(SENSE_BUS_DB))
                cursor = sdb.execute(
                    "SELECT event_type, COUNT(*) FROM events WHERE created_at > datetime('now', '-1 day') "
                    "GROUP BY event_type HAVING COUNT(*) >= 3"
                )
                for row in cursor.fetchall():
                    event_type, count = row
                    discoveries.append({
                        "type": "sense_signal",
                        "title": f"事件 {event_type} 24h内出现 {count} 次",
                        "priority": 2,
                    })
                sdb.close()
            except Exception:
                pass

        # 3c. 陈旧文件检测 (>7天未更新的关键状态文件)
        key_files = ["v15-rules-stats.json", "custom-rules.json"]
        for fname in key_files:
            f = STATE_DIR / fname
            if f.exists():
                age_days = (time.time() - f.stat().st_mtime) / 86400
                if age_days > 7:
                    discoveries.append({
                        "type": "stale_file",
                        "title": f"{fname} 已 {age_days:.0f} 天未更新",
                        "priority": 2,
                    })

        # 持久化发现
        for d in discoveries:
            if self._discovery_exists(d["type"], d["title"]):
                continue
            self._db.execute(
                "INSERT INTO discoveries (discovery_type, title, detail, priority) VALUES (?, ?, ?, ?)",
                (d["type"], d["title"], json.dumps(d, ensure_ascii=False), d.get("priority", 1))
            )
        self._db.commit()

        return discoveries

    # ── 4. 全量扫描 ──

    def scan(self) -> dict:
        """全量扫描: 模式 + 预取 + 发现 + 模块集成"""
        patterns = self.analyze_time_patterns()
        prefetches = self.prefetch()
        discoveries = self.discover()
        integration = self.integrate_modules()
        return {
            "timestamp": datetime.now().isoformat(),
            "patterns": len(patterns),
            "prefetches": len(prefetches),
            "discoveries": len(discoveries) + integration.get("discoveries_added", 0),
            "discovery_details": discoveries,
            "integration": integration,
        }

    # ── 查询接口 ──

    def get_patterns(self, limit: int = 20) -> list:
        cursor = self._db.execute(
            "SELECT pattern_type, description, frequency, confidence, last_seen "
            "FROM patterns ORDER BY confidence DESC, frequency DESC LIMIT ?", (limit,)
        )
        return [{"type": r[0], "desc": r[1], "freq": r[2], "confidence": r[3], "last_seen": r[4]}
                for r in cursor.fetchall()]

    def get_discoveries(self, limit: int = 20) -> list:
        cursor = self._db.execute(
            "SELECT discovery_type, title, priority, status, created_at "
            "FROM discoveries ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [{"type": r[0], "title": r[1], "priority": r[2], "status": r[3], "created_at": r[4]}
                for r in cursor.fetchall()]

    def get_stats(self) -> dict:
        patterns_cnt = self._db.execute("SELECT COUNT(*) FROM patterns").fetchone()[0]
        discoveries_cnt = self._db.execute("SELECT COUNT(*) FROM discoveries").fetchone()[0]
        prefetch_cnt = self._db.execute("SELECT COUNT(*) FROM prefetch_log").fetchone()[0]
        return {
            "patterns": patterns_cnt,
            "discoveries": discoveries_cnt,
            "prefetches": prefetch_cnt,
            "prefetch_effectiveness": self.get_prefetch_effectiveness(),
            "discovery_lifecycle": self.get_discovery_lifecycle_stats(),
            "quality": self.get_quality_metrics(),
        }

    # ── Prefetch Effectiveness ──

    def record_prefetch_hit(self, cache_key: str):
        """Mark a prefetch as hit (actually used)"""
        self._db.execute(
            "UPDATE prefetch_log SET hit=1 WHERE cache_key=? AND hit=0 "
            "ORDER BY created_at DESC LIMIT 1", (cache_key,)
        )
        self._db.commit()

    def get_prefetch_effectiveness(self) -> dict:
        """Calculate prefetch hit rate and stats"""
        total = self._db.execute("SELECT COUNT(*) FROM prefetch_log").fetchone()[0]
        if total == 0:
            return {"total": 0, "hits": 0, "hit_rate": 0.0,
                    "recent_7d": {"total": 0, "hits": 0, "hit_rate": 0.0},
                    "avg_latency_ms": 0.0}
        hits = self._db.execute("SELECT COUNT(*) FROM prefetch_log WHERE hit=1").fetchone()[0]
        # Recent (7d) effectiveness
        recent_total = self._db.execute(
            "SELECT COUNT(*) FROM prefetch_log WHERE created_at > datetime('now', '-7 days')"
        ).fetchone()[0]
        recent_hits = self._db.execute(
            "SELECT COUNT(*) FROM prefetch_log WHERE hit=1 AND created_at > datetime('now', '-7 days')"
        ).fetchone()[0]
        avg_latency = self._db.execute(
            "SELECT AVG(latency_ms) FROM prefetch_log WHERE latency_ms > 0"
        ).fetchone()[0] or 0
        return {
            "total": total, "hits": hits,
            "hit_rate": round(hits / total, 3) if total > 0 else 0.0,
            "recent_7d": {"total": recent_total, "hits": recent_hits,
                          "hit_rate": round(recent_hits / recent_total, 3) if recent_total > 0 else 0.0},
            "avg_latency_ms": round(avg_latency, 1),
        }

    # ── Discovery Lifecycle ──

    def transition_discovery(self, discovery_id: int, new_status: str, note: str = "") -> dict:
        """Transition a discovery through its lifecycle"""
        if new_status not in DISCOVERY_LIFECYCLE:
            return {"ok": False, "error": f"Invalid status: {new_status}"}
        row = self._db.execute(
            "SELECT status FROM discoveries WHERE id=?", (discovery_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "error": f"Discovery {discovery_id} not found"}
        current = row[0]
        valid_next = DISCOVERY_TRANSITIONS.get(current, [])
        if new_status not in valid_next:
            return {"ok": False, "error": f"Cannot transition from '{current}' to '{new_status}'",
                    "valid": valid_next}
        resolved_at = datetime.now().isoformat() if new_status in ("resolved", "archived") else None
        self._db.execute(
            "UPDATE discoveries SET status=?, resolution_note=?, resolved_at=? WHERE id=?",
            (new_status, note, resolved_at, discovery_id)
        )
        self._db.commit()
        return {"ok": True, "from": current, "to": new_status}

    def get_discovery_lifecycle_stats(self) -> dict:
        """Stats on discovery lifecycle"""
        by_status = {}
        for row in self._db.execute(
            "SELECT status, COUNT(*) FROM discoveries GROUP BY status"
        ):
            by_status[row[0]] = row[1]
        # Average time to resolve
        avg_resolve = self._db.execute(
            "SELECT AVG(julianday(resolved_at) - julianday(created_at)) "
            "FROM discoveries WHERE resolved_at IS NOT NULL"
        ).fetchone()[0]
        return {
            "by_status": by_status,
            "avg_resolve_days": round(avg_resolve, 1) if avg_resolve else None,
            "open_count": sum(v for k, v in by_status.items() if k not in ("resolved", "archived")),
        }

    # ── Real Module Integration ──

    def integrate_modules(self) -> dict:
        """Pull real data from other V15 modules for discovery"""
        results = {"sources": [], "discoveries_added": 0}

        # Skill Forge: check for skills stuck in spark/draft
        try:
            import importlib.util
            sf_path = Path(__file__).parent / "skill-forge-v15.py"
            if sf_path.exists():
                spec = importlib.util.spec_from_file_location("sf", str(sf_path))
                sf = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sf)
                forge = sf.SkillForge()
                skills = forge.scan()
                spark_count = sum(1 for s in skills.values() if s.lifecycle_stage == "spark")
                if spark_count > 10:
                    title = f"{spark_count} skills stuck in spark stage"
                    if not self._discovery_exists("skill_lifecycle", title):
                        self._db.execute(
                            "INSERT INTO discoveries (discovery_type, title, detail, priority) VALUES (?, ?, ?, ?)",
                            ("skill_lifecycle", title, json.dumps({"spark_count": spark_count}), 2)
                        )
                        results["discoveries_added"] += 1
                results["sources"].append("skill_forge")
        except Exception:
            pass

        # Daemon Loop: check for circuit breakers
        daemon_db = STATE_DIR / "v15-daemon-loop.db"
        if daemon_db.exists():
            try:
                ddb = sqlite3.connect(str(daemon_db))
                tripped = ddb.execute(
                    "SELECT COUNT(*) FROM circuit_breakers WHERE tripped=1"
                ).fetchone()[0]
                if tripped > 0:
                    title = f"{tripped} circuit breakers currently tripped"
                    if not self._discovery_exists("circuit_breaker", title):
                        self._db.execute(
                            "INSERT INTO discoveries (discovery_type, title, detail, priority) VALUES (?, ?, ?, ?)",
                            ("circuit_breaker", title, f"tripped={tripped}", 1)
                        )
                        results["discoveries_added"] += 1
                results["sources"].append("daemon_loop")
                ddb.close()
            except Exception:
                pass

        # Sense Bus: high error rate
        if SENSE_BUS_DB.exists():
            try:
                sdb = sqlite3.connect(str(SENSE_BUS_DB))
                total = sdb.execute("SELECT COUNT(*) FROM events WHERE created_at > datetime('now', '-1 day')").fetchone()[0]
                unhandled = sdb.execute(
                    "SELECT COUNT(*) FROM events WHERE status='unhandled' AND created_at > datetime('now', '-1 day')"
                ).fetchone()[0]
                if total > 10 and unhandled / total > 0.5:
                    title = f"High unhandled event rate: {unhandled}/{total} ({unhandled*100//total}%)"
                    if not self._discovery_exists("event_coverage", title):
                        self._db.execute(
                            "INSERT INTO discoveries (discovery_type, title, detail, priority) VALUES (?, ?, ?, ?)",
                            ("event_coverage", title, json.dumps({"total": total, "unhandled": unhandled}), 1)
                        )
                        results["discoveries_added"] += 1
                results["sources"].append("sense_bus")
                sdb.close()
            except Exception:
                pass

        self._db.commit()
        return results

    # ── Quality Metrics ──

    def record_quality_metric(self, metric_type: str, value: float, detail: str = ""):
        self._db.execute(
            "INSERT INTO quality_metrics (metric_type, value, detail) VALUES (?, ?, ?)",
            (metric_type, value, detail)
        )
        self._db.commit()

    def get_quality_metrics(self) -> dict:
        """Aggregate quality metrics"""
        metrics = {}
        for row in self._db.execute(
            "SELECT metric_type, AVG(value), COUNT(*), MAX(created_at) "
            "FROM quality_metrics GROUP BY metric_type"
        ):
            metrics[row[0]] = {"avg": round(row[1], 3), "count": row[2], "last": row[3]}

        # Auto-compute some metrics
        pe = self.get_prefetch_effectiveness()
        if pe["total"] > 0:
            self.record_quality_metric("prefetch_hit_rate", pe["hit_rate"], f"total={pe['total']}")

        dl = self.get_discovery_lifecycle_stats()
        if dl["avg_resolve_days"] is not None:
            self.record_quality_metric("discovery_resolve_speed", dl["avg_resolve_days"])

        return metrics

    def recommend_actions(self, limit: int = 5) -> list:
        actions = []
        actions.extend(self.prefetch()[:limit])
        discoveries = self.get_discoveries(limit)
        for discovery in discoveries[:limit]:
            actions.append({
                "pattern": discovery["title"],
                "action": f"review_{discovery['type']}",
                "confidence": 0.6 if discovery["priority"] == 2 else 0.8,
                "status": discovery["status"],
            })
        return actions[:limit]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 模块级接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_engine = None

def get_engine() -> PrescienceEngine:
    global _engine
    if _engine is None:
        _engine = PrescienceEngine()
    return _engine

def scan() -> dict:
    return get_engine().scan()

def prefetch() -> list:
    return get_engine().prefetch()

def discover() -> list:
    return get_engine().discover()

def recommend_actions(limit: int = 5) -> list:
    return get_engine().recommend_actions(limit)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    engine = get_engine()

    if "--scan" in sys.argv:
        print("🔮 先知引擎 — 全量扫描...")
        result = engine.scan()
        print(f"  📊 模式: {result['patterns']}, 预取: {result['prefetches']}, 发现: {result['discoveries']}")
        if result["discovery_details"]:
            print("  发现:")
            for d in result["discovery_details"]:
                icon = "🔴" if d.get("priority") == 1 else "🟡"
                print(f"    {icon} {d['title']}")

    elif "--patterns" in sys.argv:
        patterns = engine.get_patterns()
        print(f"🕰️ 时间模式 ({len(patterns)} 条)")
        for p in patterns:
            print(f"  [{p['confidence']:.0%}] {p['type']}: {p['desc'][:60]}")

    elif "--prefetch" in sys.argv:
        results = engine.prefetch()
        print(f"📦 预取建议 ({len(results)} 条)")
        for r in results:
            print(f"  [{r['confidence']:.0%}] {r['action']}: {r['pattern'][:50]}")

    elif "--discoveries" in sys.argv:
        discoveries = engine.get_discoveries()
        print(f"💡 主动发现 ({len(discoveries)} 条)")
        for d in discoveries:
            icon = "🔴" if d["priority"] == 1 else "🟡"
            print(f"  {icon} [{d['created_at']}] {d['title']}")

    elif "--status" in sys.argv:
        stats = engine.get_stats()
        print(f"🔮 Prescience Engine V15")
        print(f"  模式数: {stats['patterns']}")
        print(f"  发现数: {stats['discoveries']}")
        print(f"  预取次数: {stats['prefetches']}")
        pe = stats.get("prefetch_effectiveness", {})
        print(f"  预取命中率: {pe.get('hit_rate', 0):.1%} ({pe.get('hits', 0)}/{pe.get('total', 0)})")
        dl = stats.get("discovery_lifecycle", {})
        print(f"  开放发现: {dl.get('open_count', 0)}")
        if dl.get('avg_resolve_days'):
            print(f"  平均解决天数: {dl['avg_resolve_days']:.1f}")

    elif "--recommend" in sys.argv:
        actions = engine.recommend_actions()
        print(json.dumps(actions, ensure_ascii=False, indent=2))

    elif "--effectiveness" in sys.argv:
        pe = engine.get_prefetch_effectiveness()
        print(json.dumps(pe, ensure_ascii=False, indent=2))

    elif "--lifecycle" in sys.argv:
        dl = engine.get_discovery_lifecycle_stats()
        print(json.dumps(dl, ensure_ascii=False, indent=2))

    elif "--integrate" in sys.argv:
        result = engine.integrate_modules()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--transition" in sys.argv:
        idx = sys.argv.index("--transition")
        if len(sys.argv) > idx + 2:
            did = int(sys.argv[idx + 1])
            new_status = sys.argv[idx + 2]
            note = sys.argv[idx + 3] if len(sys.argv) > idx + 3 else ""
            result = engine.transition_discovery(did, new_status, note)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("用法: --transition <id> <status> [note]")

    elif "--quality" in sys.argv:
        qm = engine.get_quality_metrics()
        print(json.dumps(qm, ensure_ascii=False, indent=2))

    else:
        print("V15 Prescience Engine — 先知引擎")
        print("  --scan           全量扫描")
        print("  --patterns       查看时间模式")
        print("  --prefetch       执行预取")
        print("  --discoveries    查看主动发现")
        print("  --status         状态统计")
        print("  --recommend      查看主动建议")
        print("  --effectiveness  预取命中率")
        print("  --lifecycle      发现生命周期统计")
        print("  --integrate      模块集成扫描")
        print("  --transition     迁移发现状态")
        print("  --quality        质量指标")
