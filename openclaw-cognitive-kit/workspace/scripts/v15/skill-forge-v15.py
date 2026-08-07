#!/usr/bin/env python3
"""
V15 技能锻造 — 技能发现/调度/编排/健康检查
合并: skill-scaffold-v14 + skill-orchestrator-v12 + skill-preloader-v5

职责:
  1. 技能发现: 扫描 skills/ 目录，解析 SKILL.md 元数据
  2. 技能调度: 根据 intent → skill 映射选择最佳技能
  3. 技能编排: 多技能串联 (intent_chain → skill pipeline)
  4. 健康检查: 定期验证技能可用性

用法:
  forge = SkillForge()
  skill = forge.resolve("quant_analysis")
  result = forge.execute(skill, {"stock": "茅台"})

CLI:
  python3 scripts/v15/skill-forge-v15.py --list
  python3 scripts/v15/skill-forge-v15.py --resolve "quant_analysis"
  python3 scripts/v15/skill-forge-v15.py --health
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
SKILLS_DIR = WORKSPACE / "skills"
STATE_DIR = WORKSPACE / "state"
REGISTRY_PATH = STATE_DIR / "v15-skill-forge-registry.json"
LIFECYCLE_DB_PATH = STATE_DIR / "v15-skill-lifecycle.db"

# 7-stage lifecycle: spark → draft → trial → active → scale → merge → retire
LIFECYCLE_STAGES = ["spark", "draft", "trial", "active", "scale", "merge", "retire"]
LIFECYCLE_TRANSITIONS = {
    "spark":  ["draft", "retire"],
    "draft":  ["trial", "retire"],
    "trial":  ["active", "draft", "retire"],
    "active": ["scale", "retire"],
    "scale":  ["merge", "retire"],
    "merge":  ["retire"],
    "retire": [],  # terminal
}

# 内置 intent → skill 映射
INTENT_SKILL_MAP = {
    "quant_analysis": "alpha-research",
    "investment_decision": "alpha-research",
    "xhs_content": "xhs-creator",
    "xhs_publish": "xhs-publisher",
    "video_creation": "sora-video",
    "image_generation": "qwen-image",
    "excel_operation": "excel-xlsx",
    "word_operation": "word-docx-1.0.0",
    "pdf_reading": "pdf-reader",
    "web_search": "research-suite",
    "news_search": "research-suite",
    "news_reading": "research-suite",
    "research": "research-suite",
    "deep_research": "auto-researcher",
    "send_message": "smart-messenger",
    "chart_image": "chart-image",
    "cron_management": "cron-scheduler",
    "wechat_publish": "wechat-publisher",
    "vision_reading": "vision-reader",
}


class SkillInfo:
    def __init__(self, name: str, path: Path):
        self.name = name
        self.path = path
        self.version = ""
        self.status = "unknown"
        self.description = ""
        self.triggers = []
        self.entry_point = ""
        self.healthy = True
        self.lifecycle_stage = "draft"
        self.score = 0.0
        self.last_seen = datetime.now().isoformat()
        self._parse_metadata()
        self.lifecycle_stage = self._infer_lifecycle()

    def _parse_metadata(self):
        skill_md = self.path / "SKILL.md"
        meta_json = self.path / "_meta.json"

        if meta_json.exists():
            try:
                meta = json.loads(meta_json.read_text(encoding="utf-8"))
                self.version = meta.get("version", "")
                self.status = meta.get("status", self.status)
                self.description = meta.get("description", "")
                self.triggers = meta.get("triggers", [])
                self.entry_point = meta.get("entry_point", "")
            except Exception:
                pass

        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8")
                match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
                if match:
                    frontmatter = yaml.safe_load(match.group(1)) or {}
                    self.name = frontmatter.get("name", self.name)
                    self.version = frontmatter.get("version", self.version)
                    self.status = frontmatter.get("status", self.status)
                    self.description = frontmatter.get("description", self.description)
                    if frontmatter.get("triggers") is not None:
                        self.triggers = frontmatter.get("triggers") or []
                if not self.description:
                    lines = content.split("\n")
                    for line in lines:
                        if line.startswith("# "):
                            self.description = line[2:].strip()
                            break
            except Exception:
                pass

        # 自动检测入口
        if not self.entry_point:
            for candidate in ["scripts/main.py", "scripts/search.py", "scripts/cli.py", "scripts/run.py", "main.py", "index.py", "run.py"]:
                if (self.path / candidate).exists():
                    self.entry_point = candidate
                    break

        self.healthy = bool(self.entry_point and (self.path / self.entry_point).exists())

    def _infer_lifecycle(self) -> str:
        status = str(self.status or "").lower()
        if status in {"deprecated", "retired", "archived", "incomplete"}:
            return "retire"
        if status in {"stable", "active", "production"}:
            return "active"
        if status in {"beta", "trial", "experimental"}:
            return "trial"
        if self.entry_point:
            return "draft"
        return "spark"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "version": self.version,
            "status": self.status,
            "description": self.description,
            "triggers": self.triggers,
            "entry_point": self.entry_point,
            "healthy": self.healthy,
            "lifecycle_stage": self.lifecycle_stage,
            "score": round(self.score, 2),
            "last_seen": self.last_seen,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lifecycle Manager (SQLite 持久化)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LifecycleManager:
    """7-stage lifecycle state machine with SQLite persistence"""

    def __init__(self):
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._conn = sqlite3.connect(str(LIFECYCLE_DB_PATH))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS lifecycle_state (
                skill_name TEXT PRIMARY KEY,
                stage TEXT NOT NULL DEFAULT 'spark',
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT 'system'
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS lifecycle_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                from_stage TEXT,
                to_stage TEXT NOT NULL,
                reason TEXT DEFAULT '',
                triggered_by TEXT DEFAULT 'system',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS entry_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                entry_point TEXT,
                exists_ok INTEGER DEFAULT 0,
                syntax_ok INTEGER DEFAULT 0,
                detail TEXT DEFAULT '',
                audited_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_lce_skill ON lifecycle_events(skill_name)")
        self._conn.commit()
        return self._conn

    def get_stage(self, skill_name: str) -> str:
        conn = self._get_conn()
        row = conn.execute("SELECT stage FROM lifecycle_state WHERE skill_name=?", (skill_name,)).fetchone()
        return row[0] if row else ""

    def set_stage(self, skill_name: str, stage: str, reason: str = "", by: str = "system") -> bool:
        """Set or initialize lifecycle stage (no transition validation)"""
        conn = self._get_conn()
        old = self.get_stage(skill_name)
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT INTO lifecycle_state (skill_name, stage, updated_at, updated_by) "
            "VALUES (?,?,?,?) ON CONFLICT(skill_name) DO UPDATE SET stage=?, updated_at=?, updated_by=?",
            (skill_name, stage, now, by, stage, now, by)
        )
        conn.execute(
            "INSERT INTO lifecycle_events (skill_name, from_stage, to_stage, reason, triggered_by) "
            "VALUES (?,?,?,?,?)",
            (skill_name, old or "none", stage, reason, by)
        )
        conn.commit()
        return True

    def promote(self, skill_name: str, reason: str = "", by: str = "user") -> dict:
        """Promote skill to next lifecycle stage"""
        current = self.get_stage(skill_name)
        if not current:
            return {"ok": False, "error": f"Skill {skill_name} not in lifecycle DB"}
        allowed = LIFECYCLE_TRANSITIONS.get(current, [])
        # promote = first non-retire transition
        next_stage = None
        for s in allowed:
            if s != "retire":
                next_stage = s
                break
        if not next_stage:
            return {"ok": False, "error": f"Cannot promote from '{current}' (terminal or no forward path)"}
        self.set_stage(skill_name, next_stage, reason or f"promoted from {current}", by)
        return {"ok": True, "from": current, "to": next_stage, "skill": skill_name}

    def transition(self, skill_name: str, target: str, reason: str = "", by: str = "user") -> dict:
        """Explicit transition with validation"""
        current = self.get_stage(skill_name)
        if not current:
            return {"ok": False, "error": f"Skill {skill_name} not in lifecycle DB"}
        if target not in LIFECYCLE_TRANSITIONS.get(current, []):
            return {"ok": False, "error": f"Invalid transition: {current} → {target}. Allowed: {LIFECYCLE_TRANSITIONS.get(current, [])}"}
        self.set_stage(skill_name, target, reason, by)
        return {"ok": True, "from": current, "to": target, "skill": skill_name}

    def retire(self, skill_name: str, reason: str = "", by: str = "user") -> dict:
        current = self.get_stage(skill_name)
        if current == "retire":
            return {"ok": True, "msg": "Already retired"}
        self.set_stage(skill_name, "retire", reason or "retired", by)
        return {"ok": True, "from": current, "to": "retire", "skill": skill_name}

    def merge(self, source: str, target: str, reason: str = "", by: str = "user") -> dict:
        current = self.get_stage(source)
        if current not in ("scale", "active"):
            return {"ok": False, "error": f"Can only merge from 'scale' or 'active', current='{current}'"}
        self.set_stage(source, "merge", reason or f"merged into {target}", by)
        return {"ok": True, "from": current, "to": "merge", "source": source, "target": target}

    def get_history(self, skill_name: str, limit: int = 20) -> list:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT from_stage, to_stage, reason, triggered_by, created_at "
            "FROM lifecycle_events WHERE skill_name=? ORDER BY created_at DESC LIMIT ?",
            (skill_name, limit)
        ).fetchall()
        return [{"from": r[0], "to": r[1], "reason": r[2], "by": r[3], "at": r[4]} for r in rows]

    def get_all_states(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute("SELECT skill_name, stage, updated_at FROM lifecycle_state ORDER BY skill_name").fetchall()
        return {r[0]: {"stage": r[1], "updated_at": r[2]} for r in rows}

    def audit_entry_point(self, skill_name: str, entry_point: str, skill_path: Path) -> dict:
        """Audit a skill's entry point: existence + syntax check"""
        conn = self._get_conn()
        full_path = skill_path / entry_point if entry_point else None
        exists_ok = bool(full_path and full_path.exists())
        syntax_ok = False
        detail = ""
        if exists_ok and str(full_path).endswith(".py"):
            try:
                result = subprocess.run(
                    [sys.executable, "-c", f"import py_compile; py_compile.compile('{full_path}', doraise=True)"],
                    capture_output=True, text=True, timeout=10
                )
                syntax_ok = result.returncode == 0
                if not syntax_ok:
                    detail = result.stderr[:300]
            except Exception as e:
                detail = str(e)[:200]
        elif exists_ok:
            syntax_ok = True  # non-python entry points
        else:
            detail = f"entry_point not found: {entry_point}"

        conn.execute(
            "INSERT INTO entry_audit (skill_name, entry_point, exists_ok, syntax_ok, detail) VALUES (?,?,?,?,?)",
            (skill_name, entry_point or "", 1 if exists_ok else 0, 1 if syntax_ok else 0, detail)
        )
        conn.commit()
        return {"skill": skill_name, "entry_point": entry_point, "exists": exists_ok, "syntax": syntax_ok, "detail": detail}

    def get_stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM lifecycle_state").fetchone()[0]
        by_stage = {}
        for row in conn.execute("SELECT stage, COUNT(*) FROM lifecycle_state GROUP BY stage"):
            by_stage[row[0]] = row[1]
        event_count = conn.execute("SELECT COUNT(*) FROM lifecycle_events").fetchone()[0]
        audit_count = conn.execute("SELECT COUNT(*) FROM entry_audit").fetchone()[0]
        return {"total_skills": total, "by_stage": by_stage, "lifecycle_events": event_count, "entry_audits": audit_count}


class SkillForge:
    def __init__(self):
        self._skills_cache: dict[str, SkillInfo] = {}
        self._last_scan = 0
        self._lifecycle = LifecycleManager()
        os.makedirs(STATE_DIR, exist_ok=True)

    @property
    def lifecycle(self) -> LifecycleManager:
        return self._lifecycle

    def scan(self, force: bool = False) -> dict[str, SkillInfo]:
        """扫描 skills/ 目录"""
        if not force and self._skills_cache and (time.time() - self._last_scan < 300):
            return self._skills_cache

        self._skills_cache = {}
        if not SKILLS_DIR.exists():
            return self._skills_cache

        for d in sorted(SKILLS_DIR.iterdir()):
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue
            info = SkillInfo(d.name, d)
            if str(info.status).lower() in {"deprecated", "incomplete", "archived", "retired"}:
                continue
            # sync lifecycle stage from DB if exists
            db_stage = self._lifecycle.get_stage(d.name)
            if db_stage:
                info.lifecycle_stage = db_stage
            else:
                # first-time: persist inferred stage
                self._lifecycle.set_stage(d.name, info.lifecycle_stage, "initial scan", "system")
            self._skills_cache[d.name] = info

        self._last_scan = time.time()
        self._persist_registry()
        return self._skills_cache

    def _persist_registry(self):
        skills = list(self._skills_cache.values())
        lifecycle_counts = {}
        for info in skills:
            lifecycle_counts[info.lifecycle_stage] = lifecycle_counts.get(info.lifecycle_stage, 0) + 1
        payload = {
            "timestamp": datetime.now().isoformat(),
            "count": len(skills),
            "lifecycle_counts": lifecycle_counts,
            "skills": [info.to_dict() for info in sorted(skills, key=lambda x: x.name)],
        }
        REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _score_skill(self, info: SkillInfo, intent: str, candidates: list[str] | None = None) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        normalized_candidates = {c.strip() for c in (candidates or []) if c and c.strip()}
        mapped_skill = INTENT_SKILL_MAP.get(intent, "")

        if info.name in normalized_candidates or info.path.name in normalized_candidates:
            score += 100
            reasons.append("candidate_match")

        if mapped_skill and info.name == mapped_skill:
            score += 80
            reasons.append("intent_map")

        trigger_texts = [str(t) for t in (info.triggers or []) if t]
        if intent and intent in trigger_texts:
            score += 60
            reasons.append("trigger_exact")
        elif intent and any(intent.lower() in t.lower() or t.lower() in intent.lower() for t in trigger_texts):
            score += 35
            reasons.append("trigger_fuzzy")

        if info.lifecycle_stage == "active":
            score += 15
            reasons.append("lifecycle_active")
        elif info.lifecycle_stage == "trial":
            score += 8
            reasons.append("lifecycle_trial")

        if info.healthy:
            score += 10
            reasons.append("healthy")

        if info.entry_point:
            score += 5
            reasons.append("entry_point")

        return score, reasons

    def resolve_contract(self, intent: str, candidates: list[str] | None = None) -> dict:
        skills = self.scan()
        considered = []
        selected_key = ""
        selected_info = None
        selected_reasons: list[str] = []
        selected_score = -1.0

        for key, info in skills.items():
            score, reasons = self._score_skill(info, intent, candidates)
            considered.append({
                "key": key,
                "name": info.name,
                "score": round(score, 2),
                "lifecycle_stage": info.lifecycle_stage,
                "healthy": info.healthy,
                "reasons": reasons,
            })
            if score > selected_score:
                selected_key = key
                selected_info = info
                selected_reasons = reasons
                selected_score = score

        if selected_info:
            selected_info.score = selected_score

        considered.sort(key=lambda x: x["score"], reverse=True)
        selected_dict = selected_info.to_dict() if selected_info and selected_score > 0 else None
        return {
            "intent": intent,
            "candidates": candidates or [],
            "mapped_skill": INTENT_SKILL_MAP.get(intent),
            "selected_key": selected_key if selected_dict else None,
            "selected_name": selected_info.name if selected_dict else None,
            "selected": selected_dict,
            "reason": ", ".join(selected_reasons),
            "contract_ok": bool(selected_dict and selected_info and selected_info.entry_point),
            "considered": considered[:10],
            "timestamp": datetime.now().isoformat(),
        }

    def resolve(self, intent: str, candidates: list[str] | None = None) -> SkillInfo | None:
        """根据 intent 解析最佳技能"""
        contract = self.resolve_contract(intent, candidates)
        selected_key = contract.get("selected_key")
        if not selected_key:
            return None
        return self.scan().get(selected_key)

    def execute(self, skill: SkillInfo, params: dict = None, timeout: int = 120) -> dict:
        """执行技能"""
        if not skill.entry_point:
            return {"error": f"Skill {skill.name} has no entry point", "success": False}

        entry = skill.path / skill.entry_point
        if not entry.exists():
            return {"error": f"Entry point not found: {entry}", "success": False}

        cmd = [sys.executable, str(entry)]
        if params:
            for k, v in params.items():
                cmd.extend([f"--{k}", str(v)])

        try:
            t0 = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                    cwd=str(skill.path))
            elapsed = int((time.time() - t0) * 1000)
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:5000],
                "error": result.stderr[:2000] if result.returncode != 0 else "",
                "elapsed_ms": elapsed,
                "skill": skill.name,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Timeout ({timeout}s)", "success": False, "skill": skill.name}
        except Exception as e:
            return {"error": str(e), "success": False, "skill": skill.name}

    def orchestrate(self, chain: list[dict]) -> list[dict]:
        """编排多技能管道"""
        results = []
        prev_output = ""

        for step in chain:
            skill_name = step.get("skill", "")
            skill = self.scan().get(skill_name)
            if not skill:
                results.append({"step": step, "error": f"Skill not found: {skill_name}", "success": False})
                continue

            params = step.get("params", {})
            if prev_output and step.get("depends_on", 0) > 0:
                params["context"] = prev_output[:500]

            result = self.execute(skill, params)
            results.append({"step": step, **result})

            if result.get("success"):
                prev_output = result.get("output", "")
            else:
                break  # 管道中断

        return results

    def health_check(self) -> list[dict]:
        """检查所有技能健康状态"""
        skills = self.scan(force=True)
        results = []
        for name, info in skills.items():
            checks = {
                "has_entry": bool(info.entry_point),
                "entry_exists": (info.path / info.entry_point).exists() if info.entry_point else False,
                "has_metadata": bool(info.description),
            }
            healthy = all(checks.values())
            info.healthy = healthy
            # sync from DB
            db_stage = self._lifecycle.get_stage(name)
            if db_stage:
                info.lifecycle_stage = db_stage
            results.append({"name": name, "healthy": healthy, "checks": checks, "lifecycle_stage": info.lifecycle_stage})
        self._persist_registry()
        return results

    def audit_all_entry_points(self) -> list[dict]:
        """Audit entry points for all active skills"""
        skills = self.scan(force=True)
        results = []
        for name, info in skills.items():
            r = self._lifecycle.audit_entry_point(name, info.entry_point, info.path)
            results.append(r)
        return results

    def promote_skill(self, skill_name: str, reason: str = "") -> dict:
        return self._lifecycle.promote(skill_name, reason)

    def retire_skill(self, skill_name: str, reason: str = "") -> dict:
        return self._lifecycle.retire(skill_name, reason)

    def merge_skill(self, source: str, target: str, reason: str = "") -> dict:
        return self._lifecycle.merge(source, target, reason)

    def scan_summary(self, force: bool = False) -> dict:
        skills = self.scan(force=force)
        lifecycle_counts = {}
        healthy = 0
        for info in skills.values():
            lifecycle_counts[info.lifecycle_stage] = lifecycle_counts.get(info.lifecycle_stage, 0) + 1
            if info.healthy:
                healthy += 1
        return {
            "timestamp": datetime.now().isoformat(),
            "total": len(skills),
            "healthy": healthy,
            "registry_path": str(REGISTRY_PATH),
            "lifecycle_counts": lifecycle_counts,
        }


_forge = None

def get_forge() -> SkillForge:
    global _forge
    if _forge is None:
        _forge = SkillForge()
    return _forge


if __name__ == "__main__":
    forge = get_forge()
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--resolve")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--promote")
    parser.add_argument("--retire-skill")
    parser.add_argument("--merge-source")
    parser.add_argument("--merge-target")
    parser.add_argument("--lifecycle-history")
    parser.add_argument("--lifecycle-stats", action="store_true")
    parser.add_argument("--lifecycle-all", action="store_true")
    parser.add_argument("--audit-entries", action="store_true")
    parser.add_argument("--reason", default="")
    args, _ = parser.parse_known_args()

    if args.list:
        skills = forge.scan(force=True)
        print(f"📦 技能列表 ({len(skills)} 个)")
        for name, info in sorted(skills.items()):
            icon = "✅" if info.entry_point else "⚠️"
            stage = info.lifecycle_stage
            print(f"  {icon} {name:30s} [{stage:6s}] {info.description[:45]}")
            if info.entry_point:
                print(f"      entry: {info.entry_point}")

    elif args.resolve:
        intent = args.resolve
        if intent:
            contract = forge.resolve_contract(intent)
            skill = forge.resolve(intent)
            if skill and contract.get("selected"):
                print(f"✅ {intent} → {skill.name}")
                print(json.dumps(contract, ensure_ascii=False, indent=2))
            else:
                print(f"❌ No skill for intent: {intent}")

    elif args.health:
        results = forge.health_check()
        healthy = sum(1 for r in results if r["healthy"])
        print(f"🏥 技能健康检查: {healthy}/{len(results)} 健康")
        for r in results:
            icon = "✅" if r["healthy"] else "❌"
            print(f"  {icon} {r['name']:30s} [{r['lifecycle_stage']:6s}] {r['checks']}")

    elif args.scan:
        print(json.dumps(forge.scan_summary(force=True), ensure_ascii=False, indent=2))

    elif args.promote:
        result = forge.promote_skill(args.promote, args.reason)
        if result.get("ok"):
            print(f"⬆️  {args.promote}: {result['from']} → {result['to']}")
        else:
            print(f"❌ {result.get('error', 'unknown error')}")

    elif args.retire_skill:
        result = forge.retire_skill(args.retire_skill, args.reason)
        if result.get("ok"):
            print(f"🪦 {args.retire_skill}: {result.get('from', '?')} → retire")
        else:
            print(f"❌ {result.get('error', 'unknown')}")

    elif args.merge_source and args.merge_target:
        result = forge.merge_skill(args.merge_source, args.merge_target, args.reason)
        if result.get("ok"):
            print(f"🔀 {args.merge_source} → merged (target: {args.merge_target})")
        else:
            print(f"❌ {result.get('error', 'unknown')}")

    elif args.lifecycle_history:
        history = forge.lifecycle.get_history(args.lifecycle_history)
        print(f"📜 {args.lifecycle_history} lifecycle history ({len(history)} events)")
        for h in history:
            print(f"  [{h['at']}] {h['from']} → {h['to']}  ({h['reason']}) by {h['by']}")

    elif args.lifecycle_all:
        states = forge.lifecycle.get_all_states()
        print(f"📋 Lifecycle states ({len(states)})")
        for name, info in sorted(states.items()):
            print(f"  {name:30s} [{info['stage']:6s}]  updated: {info['updated_at']}")

    elif args.lifecycle_stats:
        stats = forge.lifecycle.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif args.audit_entries:
        results = forge.audit_all_entry_points()
        ok = sum(1 for r in results if r["exists"] and r["syntax"])
        print(f"🔍 Entry point audit: {ok}/{len(results)} passed")
        for r in results:
            icon = "✅" if r["exists"] and r["syntax"] else "❌"
            print(f"  {icon} {r['skill']:30s} {r['entry_point'] or 'NONE':30s} {r['detail'][:50]}")

    else:
        print("V15 Skill Forge")
        print("  --list                      列出所有技能")
        print("  --resolve <intent>          解析技能")
        print("  --health                    健康检查")
        print("  --scan                      扫描并输出摘要")
        print("  --promote <skill>           晋升生命周期")
        print("  --retire-skill <skill>      退役技能")
        print("  --merge-source <s> --merge-target <t>  合并技能")
        print("  --lifecycle-history <skill>  生命周期历史")
        print("  --lifecycle-all             所有技能生命周期")
        print("  --lifecycle-stats           生命周期统计")
        print("  --audit-entries             入口点审计")

