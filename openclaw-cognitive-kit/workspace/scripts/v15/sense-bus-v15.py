#!/usr/bin/env python3
"""
V15 感知总线 — 统一事件入口 + 多通道信号汇聚 + 事件路由
合并: proactive-engine-v12.py + 事件源扫描逻辑

架构:
  [飞书消息] [微信消息] [Cron tick] [文件变化]
  [市场数据] [系统健康] [mini2 心跳] [外部 API]
       └──────────┴──────────┴───────────┘
                       │
               ┌───────┴────────┐
               │  Event Router  │
               └───────┬────────┘
                       │
        ┌──────────────┼──────────────┐
   [→ 立即响应]   [→ 后台处理]   [→ 学习信号]

用法:
  bus = SenseBus()
  bus.emit(SenseEvent(source="feishu", event_type="user_message", ...))
  bus.tick()          # 一次心跳扫描
  bus.health_check()  # 系统健康扫描

CLI:
  python3 scripts/v15/sense-bus-v15.py --tick
  python3 scripts/v15/sense-bus-v15.py --health
  python3 scripts/v15/sense-bus-v15.py --status
  python3 scripts/v15/sense-bus-v15.py --history
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
SENSE_DB = STATE_DIR / "v15-sense-bus.db"
CLUSTER_CONFIG = WORKSPACE / "config" / "v15-cluster.json"

# Schema version — bump when event structure changes
EVENT_SCHEMA_VERSION = 2

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 事件数据结构 (v2: +schema_version, +target, +strategy)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class SenseEvent:
    source: str = ""            # "feishu" | "weixin" | "cron" | "market" | "system" | "file" | "api"
    priority: int = 1           # 0=urgent, 1=normal, 2=background
    event_type: str = ""        # "user_message" | "cron_tick" | "market_alert" | "health_check" | ...
    payload: dict = field(default_factory=dict)
    timestamp: float = 0.0
    requires_response: bool = False
    event_id: str = ""
    schema_version: int = EVENT_SCHEMA_VERSION
    target: str = ""            # routing target: "cognitive_core" | "skill_forge" | "daemon" | "" (auto)
    strategy: str = ""          # processing strategy: "immediate" | "deferred" | "learning" | "" (auto)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.event_id:
            self.event_id = f"{self.source}_{self.event_type}_{int(self.timestamp * 1000)}"
        if not self.strategy:
            self.strategy = _infer_strategy(self.event_type, self.priority, self.requires_response)
        if not self.target:
            self.target = _infer_target(self.event_type)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Strategy Layer
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EVENT_STRATEGY_MAP = {
    "user_message":    "immediate",
    "health_check":    "deferred",
    "cron_tick":       "deferred",
    "file_change":     "deferred",
    "market_alert":    "immediate",
    "daemon_failure":  "immediate",
    "process_result":  "learning",
    "learning_signal": "learning",
    "trajectory":      "learning",
}

EVENT_TARGET_MAP = {
    "user_message":    "cognitive_core",
    "market_alert":    "cognitive_core",
    "health_check":    "daemon",
    "cron_tick":       "daemon",
    "file_change":     "daemon",
    "daemon_failure":  "daemon",
    "process_result":  "learning_loop",
    "learning_signal": "learning_loop",
    "trajectory":      "trajectory_recorder",
}

def _infer_strategy(event_type: str, priority: int, requires_response: bool) -> str:
    if requires_response or priority == 0:
        return "immediate"
    return EVENT_STRATEGY_MAP.get(event_type, "deferred")

def _infer_target(event_type: str) -> str:
    return EVENT_TARGET_MAP.get(event_type, "")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 感知总线
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SenseBus:
    def __init__(self):
        self._handlers = {}  # event_type → [handler_fn]
        self._routing_stats = {}  # event_type → {calls, handled, errors, total_latency_ms}
        self._db = None
        self._init_db()

    def _init_db(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        self._db = sqlite3.connect(str(SENSE_DB))
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                source TEXT,
                event_type TEXT,
                priority INTEGER,
                payload TEXT,
                requires_response INTEGER,
                created_at TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                latency_ms INTEGER,
                schema_version INTEGER DEFAULT 1,
                target TEXT DEFAULT '',
                strategy TEXT DEFAULT ''
            )
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)
        """)
        self._db.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS source_state (
                state_key TEXT PRIMARY KEY,
                state_value TEXT,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS handler_routing_stats (
                event_type TEXT PRIMARY KEY,
                total_calls INTEGER DEFAULT 0,
                handled_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                total_latency_ms INTEGER DEFAULT 0,
                last_called TEXT
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now', 'localtime')),
                description TEXT DEFAULT ''
            )
        """)
        # Apply migrations
        self._migrate_schema()
        self._db.commit()

    def _migrate_schema(self):
        """Apply schema migrations"""
        applied = set()
        try:
            for row in self._db.execute("SELECT version FROM schema_migrations"):
                applied.add(row[0])
        except Exception:
            pass

        if 2 not in applied:
            # v2: add schema_version, target, strategy columns
            for col in [("schema_version", "INTEGER DEFAULT 1"),
                        ("target", "TEXT DEFAULT ''"),
                        ("strategy", "TEXT DEFAULT ''")]:
                try:
                    self._db.execute(f"ALTER TABLE events ADD COLUMN {col[0]} {col[1]}")
                except Exception:
                    pass  # column might already exist
            self._db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (2, 'add schema_version/target/strategy')"
            )
            self._db.commit()

    # ── 事件注册 / 发射 ──

    def register(self, event_type: str, handler):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: SenseEvent) -> dict:
        """发射事件 → 路由到处理器"""
        start = time.time()
        result = {"event_id": event.event_id, "handled": False, "outputs": [],
                  "strategy": event.strategy, "target": event.target}

        # 持久化事件
        self._persist_event(event)

        # 路由到处理器
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            handlers = self._handlers.get("*", [])  # 通配符处理器

        error_count = 0
        for handler in handlers:
            try:
                output = handler(event)
                if output:
                    result["outputs"].append(output)
                result["handled"] = True
            except Exception as e:
                result["outputs"].append({"error": str(e)})
                error_count += 1

        latency_ms = int((time.time() - start) * 1000)
        result["latency_ms"] = latency_ms

        # 更新状态
        status = "handled" if result["handled"] else "unhandled"
        self._update_event_status(event.event_id, status, json.dumps(result["outputs"], ensure_ascii=False), latency_ms)

        # 更新路由统计
        self._update_routing_stats(event.event_type, result["handled"], error_count, latency_ms)

        return result

    # ── 心跳 / 健康检查 ──

    def tick(self) -> dict:
        """一次心跳扫描: 集群健康 + 主动信号"""
        results = {"timestamp": datetime.now().isoformat(), "checks": []}

        # 1. 集群节点可达性
        cluster_ok = self._check_cluster()
        results["checks"].append({"name": "cluster", "status": "ok" if cluster_ok else "degraded"})

        # 2. 磁盘空间
        disk_ok = self._check_disk()
        results["checks"].append({"name": "disk", "status": "ok" if disk_ok else "warning"})

        # 3. 状态文件新鲜度
        stale = self._check_state_freshness()
        results["checks"].append({"name": "state_freshness", "stale_files": stale})

        # 4. 发射心跳事件
        event = SenseEvent(
            source="system", event_type="cron_tick", priority=2,
            payload={"type": "heartbeat", "results": results}
        )
        self.emit(event)

        return results

    def health_check(self) -> dict:
        """深度健康检查"""
        results = {"timestamp": datetime.now().isoformat(), "status": "healthy", "issues": []}

        # 1. V15 脚本完整性
        v15_dir = WORKSPACE / "scripts" / "v15"
        expected = [
            "llm-router-v15.py", "cluster-client-v15.py", "prompt-cache-v15.py",
            "memory-fabric-v15.py", "trajectory-recorder-v15.py", "learning-loop-v15.py",
            "skill-forge-v15.py", "self-calibration-v15.py", "rule-miner-v15.py",
            "rule-engine-v15.py", "version.py",
        ]
        missing = [f for f in expected if not (v15_dir / f).exists()]
        if missing:
            results["issues"].append({"type": "missing_scripts", "files": missing})
            results["status"] = "degraded"

        # 2. 状态数据库
        dbs = ["v15-routing-log.db", "v15-learning.db", "v15-sense-bus.db"]
        for db_name in dbs:
            db_path = STATE_DIR / db_name
            if db_path.exists():
                size_mb = db_path.stat().st_size / 1024 / 1024
                if size_mb > 500:
                    results["issues"].append({"type": "db_too_large", "db": db_name, "size_mb": round(size_mb, 1)})
            # DB不存在不报警 — 首次运行会自动创建

        # 3. 集群连通
        cluster_ok = self._check_cluster()
        if not cluster_ok:
            results["issues"].append({"type": "cluster_unreachable"})
            results["status"] = "degraded"

        # 4. 配置文件
        configs = ["v15-cluster.json", "VERSION.json"]
        for cfg in configs:
            if not (WORKSPACE / "config" / cfg).exists():
                results["issues"].append({"type": "missing_config", "file": cfg})

        if results["issues"]:
            results["status"] = "degraded"

        # 发射健康事件
        event = SenseEvent(
            source="system", event_type="health_check", priority=1,
            payload=results
        )
        self.emit(event)

        return results

    def scan_sources(self) -> dict:
        results = {"timestamp": datetime.now().isoformat(), "detected": [], "events": []}
        watched_files = [
            STATE_DIR / "v15-routing-log.db",
            STATE_DIR / "v15-learning.db",
            STATE_DIR / "v15-prescience.db",
            STATE_DIR / "custom-rules.json",
        ]

        for path in watched_files:
            if not path.exists():
                continue
            stat = path.stat()
            mtime = int(stat.st_mtime)
            state_key = f"file:{path.name}"
            previous = self._get_state(state_key)
            previous_mtime = int(previous) if previous and previous.isdigit() else 0
            if mtime > previous_mtime:
                event = SenseEvent(
                    source="file",
                    event_type="file_change",
                    priority=2,
                    payload={"path": str(path), "mtime": mtime, "size": stat.st_size},
                )
                emit_result = self.emit(event)
                results["detected"].append({"type": "file_change", "path": str(path.name), "mtime": mtime})
                results["events"].append(emit_result)
            self._set_state(state_key, str(mtime))

        daemon_db = STATE_DIR / "v15-daemon-loop.db"
        if daemon_db.exists():
            try:
                db = sqlite3.connect(str(daemon_db))
                row = db.execute(
                    "SELECT COUNT(*) FROM runs WHERE status='fail' AND created_at > datetime('now', '-1 day')"
                ).fetchone()
                fail_count = int(row[0] or 0)
                previous_fail_count = int(self._get_state("daemon_fail_count") or 0)
                if fail_count > previous_fail_count:
                    event = SenseEvent(
                        source="daemon",
                        event_type="daemon_failure",
                        priority=1,
                        payload={"fail_count": fail_count, "delta": fail_count - previous_fail_count},
                    )
                    emit_result = self.emit(event)
                    results["detected"].append({"type": "daemon_failure", "count": fail_count})
                    results["events"].append(emit_result)
                self._set_state("daemon_fail_count", str(fail_count))
                db.close()
            except Exception as e:
                results["detected"].append({"type": "daemon_failure_scan_error", "error": str(e)})

        return results

    # ── 事件查询 ──

    def get_recent(self, limit: int = 20) -> list:
        """获取最近事件"""
        cursor = self._db.execute(
            "SELECT id, source, event_type, priority, status, created_at, latency_ms "
            "FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        return [
            {"id": r[0], "source": r[1], "event_type": r[2], "priority": r[3],
             "status": r[4], "created_at": r[5], "latency_ms": r[6]}
            for r in cursor.fetchall()
        ]

    def get_stats(self) -> dict:
        """事件统计"""
        cursor = self._db.execute(
            "SELECT event_type, COUNT(*), AVG(latency_ms) FROM events GROUP BY event_type"
        )
        by_type = {}
        for row in cursor.fetchall():
            by_type[row[0]] = {"count": row[1], "avg_latency_ms": round(row[2] or 0, 1)}

        cursor = self._db.execute("SELECT COUNT(*) FROM events")
        total = cursor.fetchone()[0]

        cursor = self._db.execute(
            "SELECT COUNT(*) FROM events WHERE status='handled'"
        )
        handled = cursor.fetchone()[0]

        cursor = self._db.execute(
            "SELECT source, COUNT(*) FROM events GROUP BY source"
        )
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        # strategy breakdown
        by_strategy = {}
        try:
            for row in self._db.execute("SELECT strategy, COUNT(*) FROM events WHERE strategy!='' GROUP BY strategy"):
                by_strategy[row[0]] = row[1]
        except Exception:
            pass

        return {
            "total_events": total,
            "handled": handled,
            "unhandled": total - handled,
            "by_type": by_type,
            "by_source": by_source,
            "by_strategy": by_strategy,
            "schema_version": EVENT_SCHEMA_VERSION,
        }

    def get_routing_stats(self) -> dict:
        """Handler routing stats and coverage"""
        stats = {}
        try:
            for row in self._db.execute(
                "SELECT event_type, total_calls, handled_count, error_count, total_latency_ms, last_called "
                "FROM handler_routing_stats ORDER BY total_calls DESC"
            ):
                avg_lat = round(row[4] / row[1], 1) if row[1] > 0 else 0
                stats[row[0]] = {
                    "calls": row[1], "handled": row[2], "errors": row[3],
                    "avg_latency_ms": avg_lat, "last_called": row[5],
                }
        except Exception:
            pass
        # coverage = registered handlers vs seen event types
        registered_types = set(self._handlers.keys()) - {"*"}
        seen_types = set(stats.keys())
        return {
            "routing_stats": stats,
            "registered_handlers": sorted(registered_types),
            "seen_event_types": sorted(seen_types),
            "coverage": {
                "registered": len(registered_types),
                "seen": len(seen_types),
                "uncovered": sorted(seen_types - registered_types - {"*"}),
            },
        }

    # ── 内部方法 ──

    def _persist_event(self, event: SenseEvent):
        try:
            self._db.execute(
                "INSERT OR IGNORE INTO events (id, source, event_type, priority, payload, "
                "requires_response, created_at, schema_version, target, strategy) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, event.source, event.event_type, event.priority,
                 json.dumps(event.payload, ensure_ascii=False),
                 1 if event.requires_response else 0,
                 datetime.fromtimestamp(event.timestamp).isoformat(),
                 event.schema_version, event.target, event.strategy)
            )
            self._db.commit()
        except Exception:
            pass

    def _update_routing_stats(self, event_type: str, handled: bool, errors: int, latency_ms: int):
        try:
            now = datetime.now().isoformat()
            self._db.execute(
                "INSERT INTO handler_routing_stats (event_type, total_calls, handled_count, error_count, total_latency_ms, last_called) "
                "VALUES (?, 1, ?, ?, ?, ?) "
                "ON CONFLICT(event_type) DO UPDATE SET "
                "total_calls = total_calls + 1, "
                "handled_count = handled_count + ?, "
                "error_count = error_count + ?, "
                "total_latency_ms = total_latency_ms + ?, "
                "last_called = ?",
                (event_type, 1 if handled else 0, errors, latency_ms, now,
                 1 if handled else 0, errors, latency_ms, now)
            )
            self._db.commit()
        except Exception:
            pass

    def _update_event_status(self, event_id: str, status: str, result: str, latency_ms: int):
        try:
            self._db.execute(
                "UPDATE events SET status=?, result=?, latency_ms=? WHERE id=?",
                (status, result, latency_ms, event_id)
            )
            self._db.commit()
        except Exception:
            pass

    def _check_cluster(self) -> bool:
        """检查集群节点可达性"""
        try:
            from urllib.request import urlopen
            if CLUSTER_CONFIG.exists():
                with open(CLUSTER_CONFIG) as f:
                    cfg = json.load(f)
                for node_name, node_cfg in cfg.get("cluster", {}).items():
                    url = node_cfg.get("omlx_url", "")
                    if url:
                        try:
                            urlopen(url, timeout=3)
                        except Exception:
                            return False
            return True
        except Exception:
            return True  # 配置缺失不算错

    def _check_disk(self) -> bool:
        """检查磁盘空间"""
        try:
            st = os.statvfs(str(WORKSPACE))
            free_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)
            return free_gb > 5.0
        except Exception:
            return True

    def _check_state_freshness(self) -> list:
        """检查状态文件是否陈旧 (>48h 未更新)"""
        stale = []
        threshold = time.time() - 48 * 3600
        for f in STATE_DIR.glob("*.db"):
            if f.stat().st_mtime < threshold:
                stale.append(f.name)
        return stale

    def cleanup(self, days: int = 30):
        """清理旧事件"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self._db.execute("DELETE FROM events WHERE created_at < ?", (cutoff,))
        self._db.commit()

    def _get_state(self, state_key: str) -> str:
        row = self._db.execute(
            "SELECT state_value FROM source_state WHERE state_key=?", (state_key,)
        ).fetchone()
        return row[0] if row else ""

    def _set_state(self, state_key: str, value: str):
        self._db.execute(
            "INSERT INTO source_state (state_key, state_value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(state_key) DO UPDATE SET state_value=excluded.state_value, updated_at=excluded.updated_at",
            (state_key, value, datetime.now().isoformat())
        )
        self._db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 模块级接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_bus = None

def get_bus() -> SenseBus:
    global _bus
    if _bus is None:
        _bus = SenseBus()
    return _bus

def emit(event: SenseEvent) -> dict:
    return get_bus().emit(event)

def tick() -> dict:
    return get_bus().tick()

def health_check() -> dict:
    return get_bus().health_check()

def scan_sources() -> dict:
    return get_bus().scan_sources()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    bus = get_bus()

    if "--tick" in sys.argv:
        print("🫀 执行心跳扫描...")
        results = bus.tick()
        for check in results["checks"]:
            icon = "✅" if check.get("status") == "ok" else "⚠️"
            print(f"  {icon} {check['name']}: {check.get('status', json.dumps(check, ensure_ascii=False))}")

    elif "--health" in sys.argv:
        print("🏥 深度健康检查...")
        results = bus.health_check()
        print(f"  状态: {results['status']}")
        if results["issues"]:
            for issue in results["issues"]:
                print(f"  ⚠️  {issue['type']}: {json.dumps(issue, ensure_ascii=False)}")
        else:
            print("  ✅ 所有检查通过")

    elif "--status" in sys.argv:
        stats = bus.get_stats()
        print(f"📊 Sense Bus V15")
        print(f"  总事件: {stats['total_events']}")
        print(f"  已处理: {stats['handled']}")
        print(f"  未处理: {stats['unhandled']}")
        if stats["by_type"]:
            print(f"  按类型:")
            for t, info in stats["by_type"].items():
                print(f"    {t}: {info['count']}次, 平均{info['avg_latency_ms']}ms")

    elif "--history" in sys.argv:
        events = bus.get_recent(20)
        print(f"📜 最近事件 ({len(events)} 条)")
        for e in events:
            icon = "✅" if e["status"] == "handled" else "⏳"
            print(f"  {icon} [{e['source']}] {e['event_type']} (p={e['priority']}) {e['created_at']}")

    elif "--scan" in sys.argv:
        result = bus.scan_sources()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif "--cleanup" in sys.argv:
        bus.cleanup(30)
        print("🧹 已清理30天前的旧事件")

    elif "--routing-stats" in sys.argv:
        stats = bus.get_routing_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif "--strategy-map" in sys.argv:
        print("📋 Event Strategy Map:")
        print(f"  Schema version: {EVENT_SCHEMA_VERSION}")
        for et, strat in sorted(EVENT_STRATEGY_MAP.items()):
            target = EVENT_TARGET_MAP.get(et, "")
            print(f"  {et:25s} → strategy={strat:12s} target={target}")

    else:
        print("V15 Sense Bus — 感知总线")
        print("  --tick           心跳扫描")
        print("  --health         深度健康检查")
        print("  --status         事件统计")
        print("  --history        最近事件")
        print("  --scan           扫描真实事件源")
        print("  --cleanup        清理旧事件")
        print("  --routing-stats  处理器路由统计")
        print("  --strategy-map   策略映射表")
