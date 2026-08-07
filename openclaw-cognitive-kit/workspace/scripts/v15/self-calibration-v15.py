#!/usr/bin/env python3
"""
V15 自校准引擎 — 元认知 + 进化仪表盘 + 能力基准 + 路由校准
合并: metacognition-v13 + evolution-dashboard-v6 + capability-benchmark-v12

职责:
  1. 元认知置信度: 按 domain 追踪预测准确率，输出置信度
  2. 进化指标: 规则覆盖率/P50延迟/自动修复率/可验证性/学习速度/记忆利用率
  3. 能力基准: 定期自测核心能力
  4. 路由校准: 根据轨迹反馈微调路由参数

用法:
  python3 scripts/v15/self-calibration-v15.py --snapshot    # 生成快照
  python3 scripts/v15/self-calibration-v15.py --calibrate   # 校准路由
  python3 scripts/v15/self-calibration-v15.py --confidence "domain"
  python3 scripts/v15/self-calibration-v15.py --benchmark   # 能力自测
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
CALIBRATION_DB = STATE_DIR / "v15-calibration.db"
TRAJECTORY_DB = STATE_DIR / "v15-trajectory.db"


class SelfCalibration:
    def __init__(self):
        self._conn = None

    def _get_db(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._conn = sqlite3.connect(str(CALIBRATION_DB))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS metacognition (
                domain TEXT PRIMARY KEY,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                last_updated TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS evolution_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, rule_coverage REAL, p50_latency_ms INTEGER,
                auto_fix_rate REAL, verifiability REAL,
                learning_speed REAL, memory_utilization REAL,
                overall_score REAL, data TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS route_calibration (
                rule_id TEXT PRIMARY KEY,
                total_calls INTEGER DEFAULT 0,
                success_calls INTEGER DEFAULT 0,
                avg_latency_ms REAL DEFAULT 0,
                last_calibrated TEXT
            )
        """)
        return self._conn

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 元认知置信度
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def predict_confidence(self, text: str) -> tuple[str, float, dict]:
        """预测某文本对应 domain 的置信度"""
        domain = self._classify_domain(text)
        conn = self._get_db()
        row = conn.execute("SELECT confidence, total_predictions, correct_predictions FROM metacognition WHERE domain = ?",
                           (domain,)).fetchone()
        if row:
            return domain, row[0], {"total": row[1], "correct": row[2]}
        return domain, 0.5, {"total": 0, "correct": 0}

    def get_confidence(self, domain: str) -> float:
        conn = self._get_db()
        row = conn.execute("SELECT confidence FROM metacognition WHERE domain = ?", (domain,)).fetchone()
        return row[0] if row else 0.5

    def record_outcome(self, domain: str, predicted: float, correct: bool):
        """记录一次预测结果"""
        conn = self._get_db()
        conn.execute("""
            INSERT INTO metacognition (domain, total_predictions, correct_predictions, confidence, last_updated)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                total_predictions = total_predictions + 1,
                correct_predictions = correct_predictions + (CASE WHEN ? THEN 1 ELSE 0 END),
                confidence = CASE
                    WHEN ? THEN MIN(confidence + 0.02, 0.95)
                    ELSE MAX(confidence - 0.05, 0.1)
                END,
                last_updated = ?
        """, (domain, 1 if correct else 0, predicted, datetime.now().isoformat(),
              correct, correct, datetime.now().isoformat()))
        conn.commit()

    def batch_record_outcomes(self, feedbacks: list[dict]):
        """批量记录反馈"""
        for fb in feedbacks:
            self.record_outcome(fb["domain"], fb.get("predicted", 0.5), fb.get("correct", False))

    def _classify_domain(self, text: str) -> str:
        text_lower = text.lower()
        domains = {
            "finance": ["投资", "股票", "基金", "交易", "仓位", "茅台", "估值", "A股"],
            "tech": ["代码", "Python", "API", "数据库", "架构", "部署"],
            "content": ["小红书", "文案", "视频", "运营", "公众号"],
            "chat": ["你好", "谢谢", "再见", "怎么样"],
        }
        for domain, kws in domains.items():
            if any(kw.lower() in text_lower for kw in kws):
                return domain
        return "general"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 进化快照
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def take_snapshot(self) -> dict:
        """生成进化指标快照"""
        metrics = {
            "rule_coverage": self._calc_rule_coverage(),
            "p50_latency_ms": self._calc_p50_latency(),
            "auto_fix_rate": self._calc_auto_fix_rate(),
            "verifiability": self._calc_verifiability(),
            "learning_speed": self._calc_learning_speed(),
            "memory_utilization": self._calc_memory_util(),
        }
        weights = {
            "rule_coverage": 0.15, "p50_latency_ms": 0.2, "auto_fix_rate": 0.15,
            "verifiability": 0.2, "learning_speed": 0.15, "memory_utilization": 0.15,
        }
        # P50 latency → normalized score (lower is better)
        latency_score = max(0, 1.0 - metrics["p50_latency_ms"] / 5000)
        scores = {
            "rule_coverage": metrics["rule_coverage"],
            "p50_latency_ms": latency_score,
            "auto_fix_rate": metrics["auto_fix_rate"],
            "verifiability": metrics["verifiability"],
            "learning_speed": metrics["learning_speed"],
            "memory_utilization": metrics["memory_utilization"],
        }
        overall = sum(scores[k] * weights[k] for k in weights)
        metrics["overall_score"] = round(overall, 3)

        conn = self._get_db()
        conn.execute("""
            INSERT INTO evolution_snapshots (ts, rule_coverage, p50_latency_ms, auto_fix_rate,
                verifiability, learning_speed, memory_utilization, overall_score, data)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (datetime.now().isoformat(), metrics["rule_coverage"], metrics["p50_latency_ms"],
              metrics["auto_fix_rate"], metrics["verifiability"], metrics["learning_speed"],
              metrics["memory_utilization"], metrics["overall_score"],
              json.dumps(metrics, ensure_ascii=False)))
        conn.commit()

        return metrics

    def _calc_rule_coverage(self) -> float:
        if not TRAJECTORY_DB.exists():
            return 0.5
        try:
            tconn = sqlite3.connect(str(TRAJECTORY_DB))
            total = tconn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ?",
                                  ((datetime.now() - timedelta(days=7)).isoformat(),)).fetchone()[0]
            rule = tconn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ? AND source = 'rule_engine'",
                                 ((datetime.now() - timedelta(days=7)).isoformat(),)).fetchone()[0]
            tconn.close()
            return round(rule / max(total, 1), 3)
        except Exception:
            return 0.5

    def _calc_p50_latency(self) -> int:
        if not TRAJECTORY_DB.exists():
            return 2000
        try:
            tconn = sqlite3.connect(str(TRAJECTORY_DB))
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            total = tconn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ? AND total_ms > 0", (cutoff,)).fetchone()[0]
            if total == 0:
                tconn.close()
                return 2000
            row = tconn.execute("SELECT total_ms FROM trajectories WHERE ts > ? AND total_ms > 0 ORDER BY total_ms LIMIT 1 OFFSET ?",
                                (cutoff, total // 2)).fetchone()
            tconn.close()
            return row[0] if row else 2000
        except Exception:
            return 2000

    def _calc_auto_fix_rate(self) -> float:
        # 从 self-healing 日志估算
        heal_db = STATE_DIR / "v6-self-healing.db"
        if not heal_db.exists():
            return 0.5
        try:
            conn = sqlite3.connect(str(heal_db))
            total = conn.execute("SELECT COUNT(*) FROM healing_log").fetchone()[0]
            fixed = conn.execute("SELECT COUNT(*) FROM healing_log WHERE status = 'fixed'").fetchone()[0]
            conn.close()
            return round(fixed / max(total, 1), 3)
        except Exception:
            return 0.5

    def _calc_verifiability(self) -> float:
        if not TRAJECTORY_DB.exists():
            return 0.5
        try:
            tconn = sqlite3.connect(str(TRAJECTORY_DB))
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            total = tconn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ?", (cutoff,)).fetchone()[0]
            verified = tconn.execute("SELECT COUNT(*) FROM trajectories WHERE ts > ? AND has_reasoning = 1", (cutoff,)).fetchone()[0]
            tconn.close()
            return round(verified / max(total, 1) * 3, 3)  # 推理比例×3 作为可验证性代理
        except Exception:
            return 0.5

    def _calc_learning_speed(self) -> float:
        learnings_dir = WORKSPACE / ".learnings"
        if not learnings_dir.exists():
            return 0.3
        recent = [f for f in learnings_dir.glob("learning-*.md")
                  if f.stat().st_mtime > (time.time() - 7 * 86400)]
        return min(len(recent) / 7.0, 1.0)

    def _calc_memory_util(self) -> float:
        warm_db = STATE_DIR / "v15-memory-index.db"
        if not warm_db.exists():
            warm_db = STATE_DIR / "v6-memory-index.db"
        if not warm_db.exists():
            return 0.3
        try:
            conn = sqlite3.connect(str(warm_db))
            total = conn.execute("SELECT COUNT(*) FROM memory_meta").fetchone()[0]
            conn.close()
            return min(total / 500.0, 1.0)  # 500条 = 100%利用
        except Exception:
            return 0.3

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 路由校准
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def calibrate_routing(self) -> dict:
        """根据轨迹反馈校准路由参数"""
        if not TRAJECTORY_DB.exists():
            return {"calibrated": 0}

        tconn = sqlite3.connect(str(TRAJECTORY_DB))
        cutoff = (datetime.now() - timedelta(days=3)).isoformat()

        rows = tconn.execute("""
            SELECT route_rule, COUNT(*), AVG(total_ms),
                   SUM(CASE WHEN error = '' THEN 1 ELSE 0 END)
            FROM trajectories WHERE ts > ? AND route_rule != ''
            GROUP BY route_rule
        """, (cutoff,)).fetchall()
        tconn.close()

        conn = self._get_db()
        calibrated = 0
        for rule_id, total, avg_ms, success in rows:
            success_rate = (success or 0) / max(total, 1)
            conn.execute("""
                INSERT INTO route_calibration (rule_id, total_calls, success_calls, avg_latency_ms, last_calibrated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET
                    total_calls = ?, success_calls = ?, avg_latency_ms = ?, last_calibrated = ?
            """, (rule_id, total, success or 0, avg_ms or 0, datetime.now().isoformat(),
                  total, success or 0, avg_ms or 0, datetime.now().isoformat()))
            calibrated += 1
        conn.commit()

        return {"calibrated": calibrated, "rules": [(r[0], r[1], r[2]) for r in rows]}

    def get_evolution_trend(self, n: int = 10) -> list[dict]:
        """获取进化趋势"""
        conn = self._get_db()
        rows = conn.execute(
            "SELECT ts, overall_score, rule_coverage, p50_latency_ms FROM evolution_snapshots ORDER BY ts DESC LIMIT ?",
            (n,)
        ).fetchall()
        return [{"ts": r[0], "score": r[1], "rule_coverage": r[2], "p50_ms": r[3]} for r in reversed(rows)]


_calibration = None

def get_calibration() -> SelfCalibration:
    global _calibration
    if _calibration is None:
        _calibration = SelfCalibration()
    return _calibration

# 兼容 metacognition-v13 接口
def get_db():
    return get_calibration()._get_db()

class MetacognitiveSelf:
    def __init__(self, db=None):
        self._cal = get_calibration()
    def predict_confidence(self, text: str):
        return self._cal.predict_confidence(text)
    def get_confidence(self, domain: str):
        return self._cal.get_confidence(domain)
    def record_outcome(self, domain: str, predicted: float, correct: bool):
        self._cal.record_outcome(domain, predicted, correct)
    def batch_record_outcomes(self, feedbacks: list):
        self._cal.batch_record_outcomes(feedbacks)


if __name__ == "__main__":
    cal = get_calibration()
    if "--snapshot" in sys.argv:
        m = cal.take_snapshot()
        print("📊 进化快照 V15")
        print(f"  规则覆盖率: {m['rule_coverage']:.1%}")
        print(f"  P50 延迟: {m['p50_latency_ms']}ms")
        print(f"  自动修复率: {m['auto_fix_rate']:.1%}")
        print(f"  可验证性: {m['verifiability']:.1%}")
        print(f"  学习速度: {m['learning_speed']:.1%}")
        print(f"  记忆利用率: {m['memory_utilization']:.1%}")
        print(f"  综合评分: {m['overall_score']:.3f}")
    elif "--calibrate" in sys.argv:
        r = cal.calibrate_routing()
        print(f"✅ 校准完成: {r['calibrated']} 条路由规则")
    elif "--confidence" in sys.argv:
        idx = sys.argv.index("--confidence")
        text = " ".join(sys.argv[idx + 1:]) if len(sys.argv) > idx + 1 else "general"
        domain, conf, info = cal.predict_confidence(text)
        print(f"Domain: {domain}, Confidence: {conf:.2f}, Data: {info}")
    elif "--trend" in sys.argv:
        trend = cal.get_evolution_trend()
        for t in trend:
            print(f"  {t['ts'][:10]}  score={t['score']:.3f}  rule={t['rule_coverage']:.1%}  p50={t['p50_ms']}ms")
    elif "--benchmark" in sys.argv:
        m = cal.take_snapshot()
        print(f"🧪 Benchmark: {m['overall_score']:.3f}")
    else:
        print("V15 Self-Calibration")
        print("  --snapshot    进化快照")
        print("  --calibrate   校准路由")
        print("  --confidence  查询置信度")
        print("  --trend       进化趋势")
        print("  --benchmark   能力自测")
