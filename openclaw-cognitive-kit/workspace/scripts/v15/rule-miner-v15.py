#!/usr/bin/env python3
"""
V15 规则挖掘器 — 从轨迹/学习中自动发现和注入规则
升级自: auto-rule-injector-v6.py

职责:
  1. 从 learning-loop 的 rule_candidates 中筛选高置信规则
  2. 转化为 rule-engine 格式并注入
  3. 管理规则生命周期: candidate → testing → active → deprecated
  4. 定期清理低效规则

用法:
  python3 scripts/v15/rule-miner-v15.py --mine     # 挖掘新规则
  python3 scripts/v15/rule-miner-v15.py --inject    # 注入已确认规则
  python3 scripts/v15/rule-miner-v15.py --prune     # 清理无效规则
  python3 scripts/v15/rule-miner-v15.py --stats     # 统计
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
LEARNING_DB = STATE_DIR / "v15-learning.db"
CUSTOM_RULES_FILE = STATE_DIR / "custom-rules.json"

# 规则注入阈值
MIN_HIT_COUNT = 5
MIN_CONFIDENCE = 0.6
MAX_TESTING_RULES = 20
MAX_ACTIVE_RULES = 50


class RuleMiner:
    def __init__(self):
        self._learn_conn = None

    def _get_learn_db(self) -> sqlite3.Connection:
        if self._learn_conn is not None:
            return self._learn_conn
        if not LEARNING_DB.exists():
            return None
        self._learn_conn = sqlite3.connect(str(LEARNING_DB))
        return self._learn_conn

    def mine(self) -> list[dict]:
        """从 rule_candidates 中筛选高质量规则"""
        conn = self._get_learn_db()
        if not conn:
            return []

        rows = conn.execute("""
            SELECT id, pattern, intent, action_type, confidence, hit_count
            FROM rule_candidates
            WHERE status = 'candidate' AND hit_count >= ? AND confidence >= ?
            ORDER BY hit_count DESC LIMIT 20
        """, (MIN_HIT_COUNT, MIN_CONFIDENCE)).fetchall()

        mined = []
        for rid, pattern, intent, action_type, confidence, hits in rows:
            rule = {
                "id": f"auto_{intent}_{rid:03d}",
                "pattern": pattern,
                "intent": intent,
                "action_type": action_type,
                "confidence": confidence,
                "hit_count": hits,
                "source_id": rid,
                "status": "testing",
            }
            mined.append(rule)

        return mined

    def inject(self, dry_run: bool = False) -> dict:
        """注入已挖掘的规则到 custom-rules.json"""
        mined = self.mine()
        if not mined:
            return {"injected": 0, "message": "No rules to inject"}

        # 加载现有自定义规则
        existing = {}
        if CUSTOM_RULES_FILE.exists():
            try:
                with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("rules", []):
                    existing[r.get("id", "")] = r
            except Exception:
                pass

        # 检查数量限制
        active = sum(1 for r in existing.values() if r.get("status") == "active")
        testing = sum(1 for r in existing.values() if r.get("status") == "testing")

        injected = 0
        for rule in mined:
            if rule["id"] in existing:
                continue
            if testing >= MAX_TESTING_RULES:
                break

            existing[rule["id"]] = {
                "id": rule["id"],
                "pattern": [rule["pattern"]] if rule["pattern"] else [],
                "intent": rule["intent"],
                "action_type": rule["action_type"],
                "status": "testing",
                "confidence": rule["confidence"],
                "hit_count": 0,
                "created_at": datetime.now().isoformat(),
                "source": "rule_miner_v15",
            }
            injected += 1
            testing += 1

            # 更新 learning DB 中的状态
            conn = self._get_learn_db()
            if conn:
                conn.execute("UPDATE rule_candidates SET status = 'injected' WHERE id = ?",
                             (rule["source_id"],))

        if not dry_run and injected > 0:
            output = {
                "rules": list(existing.values()),
                "_updated": datetime.now().isoformat(),
                "_source": "rule-miner-v15",
            }
            os.makedirs(STATE_DIR, exist_ok=True)
            with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            conn = self._get_learn_db()
            if conn:
                conn.commit()

        return {"injected": injected, "total_rules": len(existing), "active": active, "testing": testing}

    def prune(self) -> dict:
        """清理低效规则"""
        if not CUSTOM_RULES_FILE.exists():
            return {"pruned": 0}

        with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        rules = data.get("rules", [])
        pruned = 0
        kept = []

        for r in rules:
            # 保留所有 active 规则
            if r.get("status") == "active":
                kept.append(r)
                continue
            # testing 规则: 超过30天无命中 → 清理
            created = r.get("created_at", "")
            hits = r.get("hit_count", 0)
            if created and hits == 0:
                try:
                    age = (datetime.now() - datetime.fromisoformat(created)).days
                    if age > 30:
                        r["status"] = "deprecated"
                        pruned += 1
                        continue
                except Exception:
                    pass
            kept.append(r)

        data["rules"] = kept
        data["_updated"] = datetime.now().isoformat()

        with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return {"pruned": pruned, "remaining": len(kept)}

    def promote_testing_rules(self) -> dict:
        """将高命中 testing 规则提升为 active"""
        if not CUSTOM_RULES_FILE.exists():
            return {"promoted": 0}

        with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        promoted = 0
        for r in data.get("rules", []):
            if r.get("status") == "testing" and r.get("hit_count", 0) >= 3:
                r["status"] = "active"
                r["promoted_at"] = datetime.now().isoformat()
                promoted += 1

        if promoted:
            data["_updated"] = datetime.now().isoformat()
            with open(CUSTOM_RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return {"promoted": promoted}

    def stats(self) -> dict:
        rules = {}
        if CUSTOM_RULES_FILE.exists():
            try:
                with open(CUSTOM_RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for r in data.get("rules", []):
                    status = r.get("status", "unknown")
                    rules[status] = rules.get(status, 0) + 1
            except Exception:
                pass

        candidates = 0
        conn = self._get_learn_db()
        if conn:
            try:
                candidates = conn.execute("SELECT COUNT(*) FROM rule_candidates WHERE status = 'candidate'").fetchone()[0]
            except Exception:
                pass

        return {"rule_status": rules, "pending_candidates": candidates}


if __name__ == "__main__":
    miner = RuleMiner()
    if "--mine" in sys.argv:
        rules = miner.mine()
        print(f"⛏️  挖掘到 {len(rules)} 条候选规则")
        for r in rules:
            print(f"  {r['id']}: {r['intent']}/{r['action_type']} (hits={r['hit_count']}, conf={r['confidence']:.2f})")
    elif "--inject" in sys.argv:
        r = miner.inject(dry_run="--dry-run" in sys.argv)
        print(f"✅ 注入 {r['injected']} 条规则 (总计 {r['total_rules']})")
    elif "--prune" in sys.argv:
        r = miner.prune()
        print(f"🧹 清理 {r['pruned']} 条无效规则, 保留 {r['remaining']}")
    elif "--promote" in sys.argv:
        r = miner.promote_testing_rules()
        print(f"⬆️  提升 {r['promoted']} 条规则为 active")
    elif "--stats" in sys.argv:
        s = miner.stats()
        print("📊 Rule Miner V15")
        print(f"  规则: {s['rule_status']}")
        print(f"  待挖掘候选: {s['pending_candidates']}")
    else:
        print("V15 Rule Miner")
        print("  --mine      挖掘候选规则")
        print("  --inject    注入规则")
        print("  --prune     清理无效规则")
        print("  --promote   提升 testing→active")
        print("  --stats     统计")
