#!/usr/bin/env python3
"""
V15 认知核心契约层 — 强结构化对象 + 降级矩阵 + 执行轨迹落库

提供:
  CognitiveRequest      — 请求结构化封装
  CognitiveResolution   — 解析结果(规则/分类/技能/记忆)
  CognitiveExecutionTrace — 完整执行轨迹
  CognitiveFallbackDecision — 降级决策记录
  FallbackMatrix        — 7种故障场景的统一降级矩阵
  TraceStore            — SQLite 执行轨迹持久化

被 cognitive-core-v15.py 导入使用
"""
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
TRACE_DB_PATH = STATE_DIR / "v15-cognitive-core.db"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 枚举
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ProcessStage(str, Enum):
    INIT = "init"
    RULE_ENGINE = "rule_engine"
    CLASSIFICATION = "classification"
    MEMORY_RETRIEVAL = "memory_retrieval"
    SKILL_RESOLUTION = "skill_resolution"
    PROMPT_ASSEMBLY = "prompt_assembly"
    ROUTING = "routing"
    LLM_EXECUTE = "llm_execute"
    QUALITY_GATE = "quality_gate"
    COMPOUND_SPLIT = "compound_split"
    COMPOUND_STEP = "compound_step"
    FINALIZE = "finalize"
    FALLBACK = "fallback"
    DONE = "done"


class FallbackReason(str, Enum):
    RULE_HIT_LLM_FAIL = "rule_hit_llm_fail"
    CLASSIFY_FAIL_NO_RULE = "classify_fail_no_rule"
    SKILL_RESOLVE_FAIL = "skill_resolve_fail"
    MEMORY_RETRIEVE_FAIL = "memory_retrieve_fail"
    PROMPT_ASSEMBLY_FAIL = "prompt_assembly_fail"
    ROUTER_UNAVAILABLE = "router_unavailable"
    FINALIZE_FAIL = "finalize_fail"
    COMPOUND_STEP_FAIL = "compound_step_fail"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 数据契约
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class CognitiveRequest:
    """请求结构化封装"""
    request_id: str = ""
    user_input: str = ""
    session_id: str = "default"
    sender_id: str = ""
    context: dict = field(default_factory=dict)
    timestamp: str = ""
    is_compound: bool = False
    sub_intents: list = field(default_factory=list)

    def __post_init__(self):
        if not self.request_id:
            self.request_id = f"req_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "user_input": self.user_input,
            "session_id": self.session_id,
            "sender_id": self.sender_id,
            "context": self.context,
            "timestamp": self.timestamp,
            "is_compound": self.is_compound,
            "sub_intents": self.sub_intents,
        }


@dataclass
class CognitiveResolution:
    """解析结果 — 规则/分类/技能/记忆的综合解析"""
    request_id: str = ""
    intent: str = "unknown"
    action_type: str = "chat"
    rule_id: Optional[str] = None
    rule_matched: bool = False
    classification: dict = field(default_factory=dict)
    memory_hits: int = 0
    memory_context: str = ""
    skill_selected: Optional[str] = None
    skill_contract_ok: bool = False
    skill_resolution: dict = field(default_factory=dict)
    compound_intent: bool = False
    compound_steps: list = field(default_factory=list)
    routing_model: str = ""
    routing_provider: str = ""
    routing_reason: str = ""
    resolve_latency_ms: int = 0
    stage_timings: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "intent": self.intent,
            "action_type": self.action_type,
            "rule_id": self.rule_id,
            "rule_matched": self.rule_matched,
            "classification": self.classification,
            "memory_hits": self.memory_hits,
            "memory_context": self.memory_context,
            "skill_selected": self.skill_selected,
            "skill_contract_ok": self.skill_contract_ok,
            "skill_resolution": self.skill_resolution,
            "compound_intent": self.compound_intent,
            "compound_steps": self.compound_steps,
            "routing_model": self.routing_model,
            "routing_provider": self.routing_provider,
            "routing_reason": self.routing_reason,
            "resolve_latency_ms": self.resolve_latency_ms,
            "stage_timings": self.stage_timings,
        }


@dataclass
class CognitiveFallbackDecision:
    """降级决策记录"""
    request_id: str = ""
    reason: str = ""
    failed_stage: str = ""
    error_detail: str = ""
    fallback_action: str = ""
    fallback_answer: str = ""
    severity: str = "medium"  # low / medium / high / critical
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "reason": self.reason,
            "failed_stage": self.failed_stage,
            "error_detail": self.error_detail,
            "fallback_action": self.fallback_action,
            "fallback_answer": self.fallback_answer,
            "severity": self.severity,
            "timestamp": self.timestamp,
        }


@dataclass
class CognitiveExecutionTrace:
    """完整执行轨迹"""
    request_id: str = ""
    request: Optional[CognitiveRequest] = None
    resolution: Optional[CognitiveResolution] = None
    fallbacks: list = field(default_factory=list)  # list[CognitiveFallbackDecision]
    stages: list = field(default_factory=list)      # list[{stage, status, duration_ms, detail}]
    answer: str = ""
    quality_score: float = 0.0
    total_latency_ms: int = 0
    model_used: str = ""
    error_count: int = 0
    timestamp: str = ""
    finalized: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def add_stage(self, stage: str, status: str, duration_ms: int = 0, detail: str = ""):
        self.stages.append({
            "stage": stage, "status": status,
            "duration_ms": duration_ms, "detail": detail[:500],
            "timestamp": datetime.now().isoformat(),
        })
        if status == "error":
            self.error_count += 1

    def add_fallback(self, fb: CognitiveFallbackDecision):
        self.fallbacks.append(fb.to_dict())

    def to_dict(self) -> dict:
        d = {
            "request_id": self.request_id,
            "request": self.request.to_dict() if self.request else None,
            "resolution": self.resolution.to_dict() if self.resolution else None,
            "fallbacks": self.fallbacks,
            "stages": self.stages,
            "answer": self.answer[:500],
            "quality_score": self.quality_score,
            "total_latency_ms": self.total_latency_ms,
            "model_used": self.model_used,
            "error_count": self.error_count,
            "timestamp": self.timestamp,
            "finalized": self.finalized,
        }
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 降级矩阵
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FALLBACK_MATRIX = {
    FallbackReason.RULE_HIT_LLM_FAIL: {
        "severity": "medium",
        "action": "use_rule_template",
        "description": "规则命中但LLM失败 → 使用规则模板回复",
    },
    FallbackReason.CLASSIFY_FAIL_NO_RULE: {
        "severity": "medium",
        "action": "default_chat_model",
        "description": "分类失败且规则未命中 → 使用默认chat模型",
    },
    FallbackReason.SKILL_RESOLVE_FAIL: {
        "severity": "low",
        "action": "skip_skill_context",
        "description": "技能解析失败 → 跳过技能上下文, 纯LLM回复",
    },
    FallbackReason.MEMORY_RETRIEVE_FAIL: {
        "severity": "low",
        "action": "skip_memory_context",
        "description": "记忆检索失败 → 跳过记忆上下文",
    },
    FallbackReason.PROMPT_ASSEMBLY_FAIL: {
        "severity": "medium",
        "action": "use_basic_prompt",
        "description": "Prompt组装失败 → 使用基础prompt",
    },
    FallbackReason.ROUTER_UNAVAILABLE: {
        "severity": "high",
        "action": "error_message",
        "description": "Router不可用 → 返回错误提示",
    },
    FallbackReason.FINALIZE_FAIL: {
        "severity": "low",
        "action": "skip_finalize",
        "description": "Finalize失败 → 跳过后处理, 直接输出",
    },
    FallbackReason.COMPOUND_STEP_FAIL: {
        "severity": "medium",
        "action": "partial_result",
        "description": "复合意图某步失败 → 返回部分结果 + 失败说明",
    },
}


def resolve_fallback(reason: FallbackReason, request_id: str = "",
                     error_detail: str = "") -> CognitiveFallbackDecision:
    """根据降级原因查表, 生成降级决策"""
    matrix_entry = FALLBACK_MATRIX.get(reason, {})
    return CognitiveFallbackDecision(
        request_id=request_id,
        reason=reason.value if isinstance(reason, FallbackReason) else str(reason),
        failed_stage=reason.value.split("_")[0] if isinstance(reason, FallbackReason) else "unknown",
        error_detail=error_detail[:500],
        fallback_action=matrix_entry.get("action", "error_message"),
        fallback_answer=matrix_entry.get("description", ""),
        severity=matrix_entry.get("severity", "medium"),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 执行轨迹持久化
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TraceStore:
    """SQLite 执行轨迹存储"""

    def __init__(self, db_path: Path = TRACE_DB_PATH):
        self._db_path = db_path
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn
        os.makedirs(self._db_path.parent, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()
        return self._conn

    def _init_tables(self):
        conn = self._conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                request_id TEXT PRIMARY KEY,
                user_input TEXT,
                session_id TEXT,
                sender_id TEXT,
                is_compound INTEGER DEFAULT 0,
                sub_intents TEXT DEFAULT '[]',
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resolutions (
                request_id TEXT PRIMARY KEY,
                intent TEXT,
                action_type TEXT,
                rule_id TEXT,
                rule_matched INTEGER DEFAULT 0,
                memory_hits INTEGER DEFAULT 0,
                skill_selected TEXT,
                skill_contract_ok INTEGER DEFAULT 0,
                compound_intent INTEGER DEFAULT 0,
                routing_model TEXT,
                routing_reason TEXT,
                resolve_latency_ms INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                model TEXT,
                provider TEXT,
                reason TEXT,
                latency_ms INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_resolutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                intent TEXT,
                skill_name TEXT,
                score REAL DEFAULT 0,
                contract_ok INTEGER DEFAULT 0,
                entry_point TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fallbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                reason TEXT,
                failed_stage TEXT,
                error_detail TEXT,
                fallback_action TEXT,
                severity TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS diagnostics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                stage TEXT,
                status TEXT,
                duration_ms INTEGER DEFAULT 0,
                detail TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS finalizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT,
                answer_preview TEXT,
                quality_score REAL DEFAULT 0,
                total_latency_ms INTEGER DEFAULT 0,
                model_used TEXT,
                error_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_diag_req ON diagnostics(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fallback_req ON fallbacks(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_routing_req ON routing_decisions(request_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_req ON skill_resolutions(request_id)")
        conn.commit()

    def save_trace(self, trace: CognitiveExecutionTrace):
        """保存完整执行轨迹"""
        conn = self._get_conn()
        now = datetime.now().isoformat()

        # requests
        if trace.request:
            r = trace.request
            conn.execute(
                "INSERT OR REPLACE INTO requests (request_id, user_input, session_id, sender_id, "
                "is_compound, sub_intents, created_at) VALUES (?,?,?,?,?,?,?)",
                (r.request_id, r.user_input[:2000], r.session_id, r.sender_id,
                 1 if r.is_compound else 0, json.dumps(r.sub_intents, ensure_ascii=False), r.timestamp)
            )

        # resolutions
        if trace.resolution:
            res = trace.resolution
            conn.execute(
                "INSERT OR REPLACE INTO resolutions (request_id, intent, action_type, rule_id, "
                "rule_matched, memory_hits, skill_selected, skill_contract_ok, compound_intent, "
                "routing_model, routing_reason, resolve_latency_ms, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (res.request_id, res.intent, res.action_type, res.rule_id,
                 1 if res.rule_matched else 0, res.memory_hits, res.skill_selected,
                 1 if res.skill_contract_ok else 0, 1 if res.compound_intent else 0,
                 res.routing_model, res.routing_reason, res.resolve_latency_ms, now)
            )

        # routing_decisions
        if trace.resolution and trace.resolution.routing_model:
            conn.execute(
                "INSERT INTO routing_decisions (request_id, model, provider, reason, latency_ms, success) "
                "VALUES (?,?,?,?,?,?)",
                (trace.request_id, trace.resolution.routing_model, trace.resolution.routing_provider,
                 trace.resolution.routing_reason, trace.total_latency_ms,
                 1 if trace.error_count == 0 else 0)
            )

        # skill_resolutions
        if trace.resolution and trace.resolution.skill_selected:
            sr = trace.resolution.skill_resolution
            conn.execute(
                "INSERT INTO skill_resolutions (request_id, intent, skill_name, score, "
                "contract_ok, entry_point) VALUES (?,?,?,?,?,?)",
                (trace.request_id, trace.resolution.intent, trace.resolution.skill_selected,
                 sr.get("score", 0) if isinstance(sr, dict) else 0,
                 1 if trace.resolution.skill_contract_ok else 0,
                 sr.get("entry_point", "") if isinstance(sr, dict) else "")
            )

        # fallbacks
        for fb in trace.fallbacks:
            if isinstance(fb, dict):
                conn.execute(
                    "INSERT INTO fallbacks (request_id, reason, failed_stage, error_detail, "
                    "fallback_action, severity) VALUES (?,?,?,?,?,?)",
                    (trace.request_id, fb.get("reason"), fb.get("failed_stage"),
                     fb.get("error_detail", "")[:500], fb.get("fallback_action"), fb.get("severity"))
                )

        # diagnostics (stages)
        for stage in trace.stages:
            conn.execute(
                "INSERT INTO diagnostics (request_id, stage, status, duration_ms, detail) "
                "VALUES (?,?,?,?,?)",
                (trace.request_id, stage.get("stage"), stage.get("status"),
                 stage.get("duration_ms", 0), stage.get("detail", "")[:500])
            )

        # finalizations
        conn.execute(
            "INSERT INTO finalizations (request_id, answer_preview, quality_score, "
            "total_latency_ms, model_used, error_count) VALUES (?,?,?,?,?,?)",
            (trace.request_id, trace.answer[:300], trace.quality_score,
             trace.total_latency_ms, trace.model_used, trace.error_count)
        )

        conn.commit()

    def get_trace(self, request_id: str) -> dict:
        """按 request_id 查询完整轨迹"""
        conn = self._get_conn()
        result = {"request_id": request_id}

        row = conn.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if row:
            cols = [d[0] for d in conn.execute("SELECT * FROM requests WHERE 0").description]
            result["request"] = dict(zip(cols, row))

        row = conn.execute("SELECT * FROM resolutions WHERE request_id=?", (request_id,)).fetchone()
        if row:
            cols = [d[0] for d in conn.execute("SELECT * FROM resolutions WHERE 0").description]
            result["resolution"] = dict(zip(cols, row))

        result["stages"] = []
        for row in conn.execute("SELECT stage, status, duration_ms, detail, created_at FROM diagnostics WHERE request_id=? ORDER BY id", (request_id,)):
            result["stages"].append({"stage": row[0], "status": row[1], "duration_ms": row[2], "detail": row[3], "created_at": row[4]})

        result["fallbacks"] = []
        for row in conn.execute("SELECT reason, failed_stage, error_detail, fallback_action, severity FROM fallbacks WHERE request_id=?", (request_id,)):
            result["fallbacks"].append({"reason": row[0], "failed_stage": row[1], "error_detail": row[2], "fallback_action": row[3], "severity": row[4]})

        row = conn.execute("SELECT answer_preview, quality_score, total_latency_ms, model_used, error_count FROM finalizations WHERE request_id=?", (request_id,)).fetchone()
        if row:
            result["finalization"] = {"answer_preview": row[0], "quality_score": row[1], "total_latency_ms": row[2], "model_used": row[3], "error_count": row[4]}

        return result

    def get_recent_traces(self, limit: int = 20) -> list:
        """最近轨迹摘要"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT f.request_id, r.user_input, res.intent, res.rule_id, f.model_used, "
            "f.total_latency_ms, f.quality_score, f.error_count, f.created_at "
            "FROM finalizations f "
            "LEFT JOIN requests r ON f.request_id = r.request_id "
            "LEFT JOIN resolutions res ON f.request_id = res.request_id "
            "ORDER BY f.created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{
            "request_id": r[0], "user_input": (r[1] or "")[:80], "intent": r[2],
            "rule_id": r[3], "model_used": r[4], "latency_ms": r[5],
            "quality_score": r[6], "error_count": r[7], "created_at": r[8],
        } for r in rows]

    def get_stats(self) -> dict:
        """轨迹统计"""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM finalizations").fetchone()[0]
        avg_latency = conn.execute("SELECT AVG(total_latency_ms) FROM finalizations").fetchone()[0]
        avg_quality = conn.execute("SELECT AVG(quality_score) FROM finalizations").fetchone()[0]
        error_traces = conn.execute("SELECT COUNT(*) FROM finalizations WHERE error_count > 0").fetchone()[0]
        fallback_count = conn.execute("SELECT COUNT(*) FROM fallbacks").fetchone()[0]

        by_intent = {}
        for row in conn.execute("SELECT intent, COUNT(*) FROM resolutions GROUP BY intent ORDER BY COUNT(*) DESC LIMIT 15"):
            by_intent[row[0] or "unknown"] = row[1]

        by_model = {}
        for row in conn.execute("SELECT model_used, COUNT(*) FROM finalizations GROUP BY model_used"):
            by_model[row[0] or "unknown"] = row[1]

        by_fallback_reason = {}
        for row in conn.execute("SELECT reason, COUNT(*) FROM fallbacks GROUP BY reason"):
            by_fallback_reason[row[0] or "unknown"] = row[1]

        return {
            "total_traces": total,
            "avg_latency_ms": round(avg_latency or 0, 1),
            "avg_quality_score": round(avg_quality or 0, 3),
            "error_traces": error_traces,
            "total_fallbacks": fallback_count,
            "by_intent": by_intent,
            "by_model": by_model,
            "by_fallback_reason": by_fallback_reason,
        }

    def cleanup(self, days: int = 30):
        """清理旧轨迹"""
        conn = self._get_conn()
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        for table in ["requests", "resolutions", "routing_decisions", "skill_resolutions",
                       "fallbacks", "diagnostics", "finalizations"]:
            try:
                conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
            except Exception:
                pass
        conn.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 复合意图拆分器
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMPOUND_SEPARATORS = ["然后", "接着", "之后", "再", "并且", "同时", "顺便", "以及"]

def split_compound_intent(text: str) -> list[str]:
    """将复合意图拆分为子步骤"""
    if not text:
        return [text]

    import re
    pattern = "|".join(re.escape(sep) for sep in COMPOUND_SEPARATORS)
    parts = re.split(pattern, text)
    steps = [p.strip() for p in parts if p.strip()]

    if len(steps) <= 1:
        return [text]
    return steps


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    import sys

    store = TraceStore()

    if "--stats" in sys.argv:
        stats = store.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    elif "--recent" in sys.argv:
        traces = store.get_recent_traces(20)
        print(f"📊 最近轨迹 ({len(traces)} 条)")
        for t in traces:
            icon = "✅" if t["error_count"] == 0 else "❌"
            print(f"  {icon} [{t['created_at']}] {t['intent']} | {t['model_used']} | {t['latency_ms']}ms | q={t['quality_score']}")
            if t["user_input"]:
                print(f"      {t['user_input']}")

    elif "--trace" in sys.argv:
        idx = sys.argv.index("--trace")
        if len(sys.argv) > idx + 1:
            trace = store.get_trace(sys.argv[idx + 1])
            print(json.dumps(trace, ensure_ascii=False, indent=2))
        else:
            print("用法: --trace <request_id>")

    elif "--cleanup" in sys.argv:
        store.cleanup(30)
        print("🧹 已清理30天前的轨迹")

    elif "--matrix" in sys.argv:
        print("📋 降级矩阵:")
        for reason, entry in FALLBACK_MATRIX.items():
            print(f"  [{entry['severity']:>8s}] {reason.value}")
            print(f"           → {entry['action']}: {entry['description']}")

    else:
        print("V15 Cognitive Contracts")
        print("  --stats    轨迹统计")
        print("  --recent   最近轨迹")
        print("  --trace <id>  查看完整轨迹")
        print("  --cleanup  清理旧轨迹")
        print("  --matrix   查看降级矩阵")
