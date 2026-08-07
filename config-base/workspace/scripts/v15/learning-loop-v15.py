#!/usr/bin/env python3
"""
V15 学习引擎 — 从轨迹和反馈中提取可复用知识
合并: reasoning-distill.py + knowledge-gap-v13.py

职责:
  1. 推理蒸馏: 从 trajectory 中提取高质量推理模式 → learnings/
  2. 知识缺口: 分析错误和低置信回复 → 识别需要学习的领域
  3. 规则候选: 从高频模式中提取规则候选 → rule-candidates/

用法:
  python3 scripts/v15/learning-loop-v15.py --distill      # 推理蒸馏
  python3 scripts/v15/learning-loop-v15.py --gaps          # 知识缺口分析
  python3 scripts/v15/learning-loop-v15.py --daily         # 每日学习循环
  python3 scripts/v15/learning-loop-v15.py --stats         # 学习统计
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
LEARNINGS_DIR = WORKSPACE / ".learnings"
TRAJECTORY_DB = STATE_DIR / "v15-trajectory.db"
LEARNING_DB = STATE_DIR / "v15-learning.db"


class LearningLoop:
    def __init__(self):
        self._conn = None

    def _get_db(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._conn = sqlite3.connect(str(LEARNING_DB))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_gaps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT, gap_type TEXT, description TEXT,
                severity TEXT DEFAULT 'medium',
                detected_at TEXT, resolved_at TEXT DEFAULT '',
                resolution TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS distilled_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT, intent TEXT, description TEXT,
                template TEXT, confidence REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT, last_used TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS rule_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT, intent TEXT, action_type TEXT,
                source TEXT, confidence REAL DEFAULT 0.5,
                hit_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'candidate',
                created_at TEXT
            )
        """)
        return self._conn

    def distill(self, days: int = 1) -> dict:
        """从轨迹中蒸馏推理模式"""
        if not TRAJECTORY_DB.exists():
            return {"distilled": 0, "message": "No trajectory data"}

        tconn = sqlite3.connect(str(TRAJECTORY_DB))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # 找到高质量推理轨迹 (有推理链 + 成功完成)
        rows = tconn.execute("""
            SELECT intent, action_type, user_input, data, total_ms
            FROM trajectories
            WHERE ts > ? AND has_reasoning = 1 AND error = ''
            ORDER BY ts DESC LIMIT 50
        """, (cutoff,)).fetchall()
        tconn.close()

        conn = self._get_db()
        distilled = 0

        for intent, action_type, user_input, data_str, total_ms in rows:
            try:
                data = json.loads(data_str) if data_str else {}
            except Exception:
                continue

            chain = data.get("reasoning_chain", {})
            synthesis = chain.get("synthesis", "")
            if not synthesis or len(synthesis) < 50:
                continue

            # 提取模式
            desc = f"[{intent}/{action_type}] {user_input[:100]} → {synthesis[:200]}"
            existing = conn.execute(
                "SELECT id FROM distilled_patterns WHERE description = ?", (desc[:200],)
            ).fetchone()
            if existing:
                conn.execute("UPDATE distilled_patterns SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
                             (datetime.now().isoformat(), existing[0]))
            else:
                conn.execute("""
                    INSERT INTO distilled_patterns (pattern_type, intent, description, template, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ("reasoning", intent, desc[:200], synthesis[:2000], 0.6, datetime.now().isoformat()))
                distilled += 1

        # 提取规则候选: 高频 intent+action_type 模式
        tconn2 = sqlite3.connect(str(TRAJECTORY_DB))
        freq = tconn2.execute("""
            SELECT intent, action_type, COUNT(*) as cnt, user_input
            FROM trajectories WHERE ts > ? AND source = 'llm_analysis'
            GROUP BY intent, action_type HAVING cnt >= 3
            ORDER BY cnt DESC LIMIT 20
        """, (cutoff,)).fetchall()
        tconn2.close()

        for intent, action_type, cnt, sample_input in freq:
            existing = conn.execute(
                "SELECT id, hit_count FROM rule_candidates WHERE intent = ? AND action_type = ?",
                (intent, action_type)
            ).fetchone()
            if existing:
                conn.execute("UPDATE rule_candidates SET hit_count = ? WHERE id = ?", (cnt, existing[0]))
            else:
                conn.execute("""
                    INSERT INTO rule_candidates (pattern, intent, action_type, source, confidence, hit_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sample_input[:100] if sample_input else "", intent, action_type,
                      "trajectory_mining", min(0.3 + cnt * 0.05, 0.9), cnt, datetime.now().isoformat()))

        conn.commit()
        return {"distilled": distilled, "freq_patterns": len(freq)}

    def analyze_gaps(self, days: int = 7) -> list[dict]:
        """分析知识缺口"""
        if not TRAJECTORY_DB.exists():
            return []

        tconn = sqlite3.connect(str(TRAJECTORY_DB))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # 找错误和低质量轨迹
        errors = tconn.execute("""
            SELECT intent, action_type, error, COUNT(*) as cnt
            FROM trajectories WHERE ts > ? AND error != ''
            GROUP BY intent, action_type, error ORDER BY cnt DESC LIMIT 20
        """, (cutoff,)).fetchall()

        # 找高延迟轨迹
        slow = tconn.execute("""
            SELECT intent, action_type, AVG(total_ms), COUNT(*)
            FROM trajectories WHERE ts > ? AND total_ms > 5000
            GROUP BY intent, action_type ORDER BY AVG(total_ms) DESC LIMIT 10
        """, (cutoff,)).fetchall()

        tconn.close()

        conn = self._get_db()
        gaps = []

        for intent, action_type, error, cnt in errors:
            gap = {
                "domain": intent, "gap_type": "error_pattern",
                "description": f"{intent}/{action_type} 错误 {cnt} 次: {error[:100]}",
                "severity": "high" if cnt >= 5 else "medium",
            }
            gaps.append(gap)
            conn.execute("""
                INSERT OR IGNORE INTO knowledge_gaps (domain, gap_type, description, severity, detected_at)
                VALUES (?, ?, ?, ?, ?)
            """, (intent, "error_pattern", gap["description"][:200], gap["severity"], datetime.now().isoformat()))

        for intent, action_type, avg_ms, cnt in slow:
            gap = {
                "domain": intent, "gap_type": "high_latency",
                "description": f"{intent}/{action_type} 平均延迟 {avg_ms:.0f}ms ({cnt} 次)",
                "severity": "medium",
            }
            gaps.append(gap)

        conn.commit()
        return gaps

    def daily_loop(self) -> dict:
        """每日学习循环 — 蒸馏 + 缺口分析 + 保存到 .learnings/"""
        distill_result = self.distill(days=1)
        gaps = self.analyze_gaps(days=7)

        # 保存今日学习到 .learnings/
        os.makedirs(LEARNINGS_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        learning_file = LEARNINGS_DIR / f"learning-{today}.md"

        content = f"# 学习记录 {today}\n\n"
        content += f"## 推理蒸馏\n- 新模式: {distill_result['distilled']}\n- 频率模式: {distill_result.get('freq_patterns', 0)}\n\n"

        if gaps:
            content += "## 知识缺口\n"
            for g in gaps[:10]:
                content += f"- [{g['severity']}] {g['description']}\n"
            content += "\n"

        # 规则候选统计
        conn = self._get_db()
        candidates = conn.execute(
            "SELECT intent, action_type, hit_count, confidence FROM rule_candidates WHERE status = 'candidate' ORDER BY hit_count DESC LIMIT 10"
        ).fetchall()
        if candidates:
            content += "## 规则候选\n"
            for intent, at, hits, conf in candidates:
                content += f"- {intent}/{at}: {hits} hits (conf: {conf:.2f})\n"

        with open(learning_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "distill": distill_result,
            "gaps": len(gaps),
            "candidates": len(candidates),
            "saved_to": str(learning_file),
        }

    def stats(self) -> dict:
        conn = self._get_db()
        patterns = conn.execute("SELECT COUNT(*) FROM distilled_patterns").fetchone()[0]
        gaps = conn.execute("SELECT COUNT(*) FROM knowledge_gaps WHERE resolved_at = ''").fetchone()[0]
        candidates = conn.execute("SELECT COUNT(*) FROM rule_candidates WHERE status = 'candidate'").fetchone()[0]
        return {"patterns": patterns, "open_gaps": gaps, "rule_candidates": candidates}


if __name__ == "__main__":
    loop = LearningLoop()
    if "--distill" in sys.argv:
        r = loop.distill()
        print(f"✅ 蒸馏完成: {r['distilled']} 新模式")
    elif "--gaps" in sys.argv:
        gaps = loop.analyze_gaps()
        print(f"🔍 知识缺口: {len(gaps)} 个")
        for g in gaps[:10]:
            print(f"  [{g['severity']}] {g['description']}")
    elif "--daily" in sys.argv:
        r = loop.daily_loop()
        print(f"✅ 每日学习完成")
        print(f"  蒸馏: {r['distill']['distilled']} 新模式")
        print(f"  缺口: {r['gaps']} 个")
        print(f"  候选: {r['candidates']} 条")
        print(f"  保存: {r['saved_to']}")
    elif "--stats" in sys.argv:
        s = loop.stats()
        print(f"📊 Learning Loop V15")
        print(f"  蒸馏模式: {s['patterns']}")
        print(f"  开放缺口: {s['open_gaps']}")
        print(f"  规则候选: {s['rule_candidates']}")
    else:
        print("V15 Learning Loop")
        print("  --distill  推理蒸馏")
        print("  --gaps     知识缺口分析")
        print("  --daily    每日学习循环")
        print("  --stats    统计")
