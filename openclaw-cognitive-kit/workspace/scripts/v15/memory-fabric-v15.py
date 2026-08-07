#!/usr/bin/env python3
"""
V15 记忆织网 — 统一记忆检索 + 对话缓存 + 向量语义 + 三温区管理
合并: memory-index-v6.py + conversation-buffer-v6.py + memory-engine-v12.py

三温区架构:
  Hot  (热区): 当前对话历史 — SQLite (session × 20条, 60min 过期)
  Warm (温区): FTS5 全文检索 — daily_memory / learnings / reasoning / patterns
  Cold (冷区): bge-m3 向量语义 — embedding_cache (mini2 oMLX)

用法:
  fabric = MemoryFabric()
  fabric.append_conversation(session_id, "user", "消息")
  history = fabric.get_history(session_id, n=5)
  memories = fabric.search("投资策略", top_k=5)

CLI:
  python3 scripts/v15/memory-fabric-v15.py --build
  python3 scripts/v15/memory-fabric-v15.py --search "关键词"
  python3 scripts/v15/memory-fabric-v15.py --stats
  python3 scripts/v15/memory-fabric-v15.py --cleanup
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import struct
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

try:
    import jieba
    jieba.setLogLevel(jieba.logging.WARNING)
    _HAS_JIEBA = True
except ImportError:
    _HAS_JIEBA = False

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
STATE_DIR = WORKSPACE / "state"
MEMORY_DIR = WORKSPACE / "memory"
LEARNINGS_DIR = WORKSPACE / ".learnings"
REASONING_DIR = WORKSPACE / ".reasoning"

# DB 路径
HOT_DB_PATH = STATE_DIR / "v15-conversation-buffer.db"
WARM_DB_PATH = STATE_DIR / "v15-memory-index.db"
GRAPH_DB_PATH = STATE_DIR / "v15-knowledge-graph.db"

MAX_HISTORY_PER_SESSION = 20
EXPIRE_MINUTES = 60
MAX_SESSIONS = 100
SUMMARIZE_THRESHOLD = 12

# 自动分类关键词
CATEGORY_KEYWORDS = {
    "finance": ["投资", "股票", "基金", "A股", "交易", "仓位", "持仓", "收益", "亏损", "估值", "茅台"],
    "tech": ["代码", "架构", "API", "Python", "数据库", "模型", "部署", "服务器", "脚本", "框架"],
    "content": ["小红书", "文案", "视频", "内容", "运营", "公众号", "自媒体"],
    "product": ["产品", "需求", "用户", "迭代", "版本", "路线图", "方案"],
    "error": ["错误", "bug", "失败", "超时", "异常", "修复", "error", "timeout"],
    "reasoning": ["分析", "评估", "决策", "比较", "权衡", "风险", "结论"],
}


def _auto_categorize(text: str) -> str:
    cats = []
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                cats.append(cat)
                break
    return ",".join(cats) if cats else "general"


def _time_decay_score(created_at: str, half_life_days: int = 30) -> float:
    if not created_at:
        return 0.5
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00").split("+")[0])
        age_days = (datetime.now() - created).total_seconds() / 86400
        return math.exp(-0.693 * age_days / half_life_days)
    except (ValueError, TypeError):
        return 0.5


def _jieba_expand_query(query: str) -> str:
    if not _HAS_JIEBA:
        return query
    words = [w for w in jieba.cut(query) if len(w.strip()) >= 2]
    if not words:
        return query
    terms = [query] + words
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(terms))


class MemoryFabric:
    """V15 统一记忆织网"""

    def __init__(self):
        self._hot_conn = None
        self._warm_conn = None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Hot Zone: 对话历史缓存
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_hot_db(self) -> sqlite3.Connection:
        if self._hot_conn is not None:
            return self._hot_conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._hot_conn = sqlite3.connect(str(HOT_DB_PATH), timeout=15, check_same_thread=False)
        self._hot_conn.execute("PRAGMA journal_mode=WAL")
        self._hot_conn.execute("PRAGMA synchronous=NORMAL")
        self._hot_conn.execute("PRAGMA busy_timeout=10000")
        self._hot_conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self._hot_conn.execute("""
            CREATE TABLE IF NOT EXISTS session_meta (
                session_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL,
                summary TEXT DEFAULT '',
                summarized_at TEXT DEFAULT ''
            )
        """)
        self._hot_conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id, id)")
        return self._hot_conn

    def append_conversation(self, session_id: str, role: str, content: str):
        now = datetime.now().isoformat()
        conn = self._get_hot_db()
        conn.execute("""
            INSERT INTO session_meta(session_id, created_at, last_active)
            VALUES(?,?,?) ON CONFLICT(session_id) DO UPDATE SET last_active=excluded.last_active
        """, (session_id, now, now))
        conn.execute("INSERT INTO messages(session_id, role, content, timestamp) VALUES(?,?,?,?)",
                     (session_id, role, content[:3000], now))
        conn.execute("""
            DELETE FROM messages WHERE session_id=? AND id NOT IN (
                SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?
            )
        """, (session_id, session_id, MAX_HISTORY_PER_SESSION))
        count = conn.execute("SELECT COUNT(*) FROM session_meta").fetchone()[0]
        if count > MAX_SESSIONS:
            old = conn.execute("SELECT session_id FROM session_meta ORDER BY last_active ASC LIMIT ?",
                               (count - MAX_SESSIONS,)).fetchall()
            for (sid,) in old:
                conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
                conn.execute("DELETE FROM session_meta WHERE session_id=?", (sid,))
        conn.commit()

    def get_history(self, session_id: str, n: int = 5) -> list[dict]:
        conn = self._get_hot_db()
        rows = conn.execute("""
            SELECT role, content, timestamp FROM (
                SELECT role, content, timestamp, id FROM messages
                WHERE session_id=? ORDER BY id DESC LIMIT ?
            ) ORDER BY id ASC
        """, (session_id, n)).fetchall()
        return [{"role": r, "content": c, "timestamp": t} for r, c, t in rows]

    def get_context_text(self, session_id: str, n: int = 5) -> str:
        messages = self.get_history(session_id, n)
        if not messages:
            return ""
        return "\n".join(f"[{m['timestamp'][:16]}] {m['role']}: {m['content'][:500]}" for m in messages)

    def summarize_session(self, session_id: str) -> str:
        conn = self._get_hot_db()
        rows = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC",
                            (session_id,)).fetchall()
        if len(rows) < SUMMARIZE_THRESHOLD:
            return ""
        user_msgs = [c for r, c in rows if r == "user"]
        parts = [f"用户提了{len(user_msgs)}个问题"]
        for msg in user_msgs[-3:]:
            parts.append(f"  - {msg[:100]}")
        summary = "\n".join(parts)
        keep_ids = conn.execute("SELECT id FROM messages WHERE session_id=? ORDER BY id DESC LIMIT 5",
                                (session_id,)).fetchall()
        keep_set = {r[0] for r in keep_ids}
        if keep_set:
            placeholders = ",".join("?" * len(keep_set))
            conn.execute(f"DELETE FROM messages WHERE session_id=? AND id NOT IN ({placeholders})",
                         (session_id, *keep_set))
        conn.execute("UPDATE session_meta SET summary=?, summarized_at=? WHERE session_id=?",
                     (summary, datetime.now().isoformat(), session_id))
        conn.commit()
        return summary

    def cleanup_expired(self):
        conn = self._get_hot_db()
        cutoff = (datetime.now() - timedelta(minutes=EXPIRE_MINUTES)).isoformat()
        expired = conn.execute("SELECT session_id FROM session_meta WHERE last_active < ?", (cutoff,)).fetchall()
        removed = 0
        for (sid,) in expired:
            msgs = conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id ASC",
                                (sid,)).fetchall()
            if len(msgs) >= 3:
                self._save_expiring_summary(sid, [{"role": r, "content": c} for r, c in msgs])
            conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
            conn.execute("DELETE FROM session_meta WHERE session_id=?", (sid,))
            removed += 1
        if removed:
            conn.commit()
        remaining = conn.execute("SELECT COUNT(*) FROM session_meta").fetchone()[0]
        return removed, remaining

    def _save_expiring_summary(self, session_id: str, msgs: list[dict]):
        user_msgs = [m["content"][:150] for m in msgs if m.get("role") == "user"]
        if not user_msgs:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        summary = f"\n### 对话摘要 {datetime.now().strftime('%H:%M')} (session: {session_id[:16]})\n"
        summary += f"用户消息 {len(user_msgs)} 条:\n"
        for msg in user_msgs[-5:]:
            summary += f"- {msg[:100]}\n"
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(MEMORY_DIR / f"{today}.md", "a", encoding="utf-8") as f:
                f.write(summary)
        except Exception:
            pass

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Warm Zone: FTS5 全文检索
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_warm_db(self) -> sqlite3.Connection:
        if self._warm_conn is not None:
            return self._warm_conn
        os.makedirs(STATE_DIR, exist_ok=True)
        self._warm_conn = sqlite3.connect(str(WARM_DB_PATH))
        self._warm_conn.execute("PRAGMA journal_mode=WAL")
        self._warm_conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                source, title, content, tags, created_at,
                tokenize='unicode61'
            )
        """)
        self._warm_conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT, title TEXT,
                content_hash TEXT UNIQUE,
                category TEXT DEFAULT '',
                indexed_at TEXT
            )
        """)
        return self._warm_conn

    def _index_entry(self, conn: sqlite3.Connection, source: str, title: str,
                     content: str, tags: str = "", created_at: str = "") -> bool:
        ch = hashlib.md5(content.encode("utf-8")).hexdigest()
        if conn.execute("SELECT id FROM memory_meta WHERE content_hash = ?", (ch,)).fetchone():
            return False
        if not created_at:
            created_at = datetime.now().isoformat()
        category = _auto_categorize(content)
        auto_tags = f"{tags},{category}" if tags else category
        conn.execute("INSERT INTO memory_fts (source, title, content, tags, created_at) VALUES (?,?,?,?,?)",
                     (source, title, content[:5000], auto_tags, created_at))
        conn.execute("INSERT INTO memory_meta (source, title, content_hash, category, indexed_at) VALUES (?,?,?,?,?)",
                     (source, title, ch, category, datetime.now().isoformat()))
        return True

    def build_index(self) -> tuple[int, int]:
        conn = self._get_warm_db()
        indexed = skipped = 0

        # 1. daily memory
        if MEMORY_DIR.exists():
            for md in sorted(MEMORY_DIR.glob("*.md")):
                content = md.read_text(encoding="utf-8", errors="ignore")
                if not content.strip():
                    continue
                dm = re.search(r"(\d{4}-\d{2}-\d{2})", md.name)
                created = dm.group(1) if dm else ""
                if self._index_entry(conn, "daily_memory", f"Daily Memory: {md.stem}", content, "memory,daily", created):
                    indexed += 1
                else:
                    skipped += 1

        # 2. learnings
        if LEARNINGS_DIR.exists():
            for md in sorted(LEARNINGS_DIR.glob("*.md")):
                content = md.read_text(encoding="utf-8", errors="ignore")
                if content.strip() and self._index_entry(conn, "learning", f"Learning: {md.stem}", content, "learning," + md.stem):
                    indexed += 1
                else:
                    skipped += 1

        # 3. reasoning
        if REASONING_DIR.exists():
            for md in sorted(REASONING_DIR.glob("*.md")):
                content = md.read_text(encoding="utf-8", errors="ignore")
                if content.strip():
                    dm = re.search(r"(\d{4}-\d{2}-\d{2})", md.name)
                    if self._index_entry(conn, "reasoning", f"Reasoning: {md.stem}", content, "reasoning", dm.group(1) if dm else ""):
                        indexed += 1
                    else:
                        skipped += 1

        # 4. reasoning-store (SQLite)
        for db_path in [WORKSPACE / "data" / "reasoning-store.db",
                        Path.home() / ".openclaw" / "workspace" / "data" / "reasoning-store.db"]:
            if db_path.exists():
                try:
                    rconn = sqlite3.connect(str(db_path))
                    for topic, conclusion, confidence, risk, created_at in rconn.execute(
                        "SELECT topic, conclusion, confidence, risk, created_at FROM reasoning_logs"
                    ):
                        combined = f"Topic: {topic}\nConclusion: {conclusion}\nConfidence: {confidence}\nRisk: {risk}"
                        if self._index_entry(conn, "reasoning_store", topic or "untitled", combined, f"reasoning_store,{confidence},{risk}", created_at or ""):
                            indexed += 1
                        else:
                            skipped += 1
                    rconn.close()
                except Exception:
                    pass
                break

        # 5. core docs
        for doc_name in ["SOUL.md", "USER.md", "MEMORY.md", "TOOLS.md", "IDENTITY.md", "AGENTS.md", "SESSION-STATE.md"]:
            doc_path = WORKSPACE / doc_name
            if doc_path.exists():
                content = doc_path.read_text(encoding="utf-8", errors="ignore")
                if content.strip() and self._index_entry(conn, "core_doc", doc_name, content, "core," + doc_name.lower()):
                    indexed += 1
                else:
                    skipped += 1

        # 6. error-tracker
        error_file = STATE_DIR / "error-tracker.json"
        if error_file.exists():
            try:
                with open(error_file, "r", encoding="utf-8") as f:
                    errors = json.load(f)
                if isinstance(errors, list):
                    for err in errors:
                        desc = err.get("description", "")
                        combined = f"Error: {desc}\nRoot: {err.get('rootCause', '')}\nFix: {err.get('fixNote', '')}"
                        if self._index_entry(conn, "error_tracker", f"ERR-{err.get('id', '?')}: {desc[:80]}", combined,
                                             f"error,{err.get('category', '')}", err.get("firstSeen", "")):
                            indexed += 1
                        else:
                            skipped += 1
            except Exception:
                pass

        # 7. pattern-library
        pl_path = STATE_DIR / "pattern-library.json"
        if pl_path.exists():
            try:
                pl_data = json.loads(pl_path.read_text(encoding="utf-8"))
                for pat in pl_data.get("patterns", []):
                    desc = pat.get("description", "")
                    combined = f"Pattern: {desc}\nAction: {pat.get('action', '')}\nConfidence: {pat.get('confidence', '')}"
                    if self._index_entry(conn, "pattern_library", desc[:80] or "pattern", combined,
                                         f"pattern,{pat.get('confidence', '')}"):
                        indexed += 1
                    else:
                        skipped += 1
            except Exception:
                pass

        # 8. LCM summaries
        lcm_db = Path.home() / ".openclaw" / "lcm.db"
        if lcm_db.exists():
            try:
                lconn = sqlite3.connect(str(lcm_db))
                for sid, content, tokens, created_at in lconn.execute("""
                    SELECT summary_id, content, token_count, created_at FROM summaries
                    WHERE content NOT LIKE '%[Fallback summary%' AND content IS NOT NULL AND LENGTH(TRIM(content)) > 50
                    ORDER BY created_at DESC LIMIT 200
                """):
                    if self._index_entry(conn, "lcm_summary", f"LCM #{sid}: {content[:60]}", content, "lcm,summary", created_at or ""):
                        indexed += 1
                    else:
                        skipped += 1
                lconn.close()
            except Exception:
                pass

        conn.commit()
        return indexed, skipped

    def search(self, query: str, top_k: int = 5, category: str = "") -> list[dict]:
        """双通道检索 — FTS5 + bge-m3 向量语义"""
        conn = self._get_warm_db()
        expanded = _jieba_expand_query(query)
        limit = top_k * 3

        try:
            rows = conn.execute("""
                SELECT source, title, snippet(memory_fts, 2, '>>>', '<<<', '...', 64), tags, created_at, rank
                FROM memory_fts WHERE memory_fts MATCH ? ORDER BY rank LIMIT ?
            """, (expanded, limit)).fetchall()
        except Exception:
            rows = conn.execute("""
                SELECT source, title, substr(content, 1, 200), tags, created_at, 0
                FROM memory_fts WHERE content LIKE ? OR title LIKE ? ORDER BY created_at DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()

        # 向量检索 (冷区, graceful降级)
        vec_results = self._vector_search(query, top_k=top_k)
        vec_sources = {v["source"] for v in vec_results[:3]}

        seen = set()
        results = []
        for source, title, snippet, tags, created_at, rank in rows:
            key = title[:40].lower()
            if key in seen:
                continue
            seen.add(key)
            if category and category not in (tags or ""):
                continue
            fts = -rank if rank else 0.1
            decay = _time_decay_score(created_at)
            boost = 0.2 if any(vs in (source or "") for vs in vec_sources) else 0
            score = fts * 0.6 + decay * 0.25 + boost
            results.append({
                "source": source, "title": title, "snippet": snippet, "tags": tags,
                "created_at": created_at, "relevance": round(score, 4),
            })

        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results[:top_k]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Cold Zone: 向量语义检索
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _vector_search(self, query: str, top_k: int = 5) -> list[dict]:
        main_db = Path.home() / ".openclaw" / "memory" / "main.sqlite"
        if not main_db.exists():
            return []
        try:
            from urllib.request import urlopen, Request
            url = os.environ.get("OMLX_EMBED_URL", "http://127.0.0.1:11434/v1/embeddings")
            data = json.dumps({"model": "bge-m3-mlx-fp16", "input": query[:500]}).encode("utf-8")
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=5) as resp:
                q_emb = json.loads(resp.read().decode("utf-8"))["data"][0]["embedding"]

            conn = sqlite3.connect(str(main_db))
            rows = conn.execute("SELECT provider_key, hash, embedding, dims FROM embedding_cache WHERE provider_key LIKE 'bridge2:%'").fetchall()
            conn.close()
            if not rows:
                return []

            scored = []
            for pkey, h, emb_blob, dims in rows:
                try:
                    emb = struct.unpack(f'{dims}f', emb_blob)
                    dot = sum(a * b for a, b in zip(q_emb, emb))
                    na = math.sqrt(sum(a * a for a in q_emb))
                    nb = math.sqrt(sum(b * b for b in emb))
                    sim = dot / (na * nb) if na > 0 and nb > 0 else 0
                    scored.append({"source": pkey.replace("bridge2:", ""), "hash": h, "similarity": sim})
                except Exception:
                    continue
            scored.sort(key=lambda x: x["similarity"], reverse=True)
            return scored[:top_k]
        except Exception:
            return []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Knowledge Graph: 显式图谱 API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _get_graph_db(self) -> sqlite3.Connection:
        if not hasattr(self, "_graph_conn") or self._graph_conn is None:
            os.makedirs(STATE_DIR, exist_ok=True)
            self._graph_conn = sqlite3.connect(str(GRAPH_DB_PATH))
            self._graph_conn.execute("PRAGMA journal_mode=WAL")
            self._graph_conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
            """)
            self._graph_conn.execute("""
                CREATE TABLE IF NOT EXISTS kg_edges (
                    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (source_id) REFERENCES kg_nodes(node_id),
                    FOREIGN KEY (target_id) REFERENCES kg_nodes(node_id)
                )
            """)
            self._graph_conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_src ON kg_edges(source_id)")
            self._graph_conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_tgt ON kg_edges(target_id)")
            self._graph_conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_rel ON kg_edges(relation)")
            self._graph_conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_edge_unique ON kg_edges(source_id, target_id, relation)")
            self._graph_conn.commit()
        return self._graph_conn

    # ── Write API ──

    def add_node(self, node_id: str, node_type: str, label: str, properties: dict = None) -> bool:
        """Add or update a node in the knowledge graph"""
        conn = self._get_graph_db()
        props_json = json.dumps(properties or {}, ensure_ascii=False)
        now = datetime.now().isoformat()
        try:
            conn.execute(
                "INSERT INTO kg_nodes (node_id, node_type, label, properties, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(node_id) DO UPDATE SET label=?, properties=?, updated_at=?",
                (node_id, node_type, label, props_json, now, now, label, props_json, now)
            )
            conn.commit()
            return True
        except Exception:
            return False

    def add_edge(self, source_id: str, target_id: str, relation: str,
                 weight: float = 1.0, properties: dict = None) -> bool:
        """Add or update an edge (relationship) in the knowledge graph"""
        conn = self._get_graph_db()
        props_json = json.dumps(properties or {}, ensure_ascii=False)
        try:
            conn.execute(
                "INSERT INTO kg_edges (source_id, target_id, relation, weight, properties) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(source_id, target_id, relation) DO UPDATE SET weight=?, properties=?",
                (source_id, target_id, relation, weight, props_json, weight, props_json)
            )
            conn.commit()
            return True
        except Exception:
            return False

    # ── Query API ──

    def query_node(self, node_id: str) -> dict | None:
        """Get a single node by ID"""
        conn = self._get_graph_db()
        row = conn.execute(
            "SELECT node_id, node_type, label, properties, created_at FROM kg_nodes WHERE node_id=?",
            (node_id,)
        ).fetchone()
        if not row:
            return None
        return {"node_id": row[0], "type": row[1], "label": row[2],
                "properties": json.loads(row[3] or "{}"), "created_at": row[4]}

    def query_neighbors(self, node_id: str, relation: str = "", direction: str = "both") -> list:
        """Find neighbors of a node, optionally filtered by relation and direction"""
        conn = self._get_graph_db()
        results = []
        if direction in ("out", "both"):
            q = "SELECT e.target_id, e.relation, e.weight, n.label, n.node_type FROM kg_edges e " \
                "JOIN kg_nodes n ON e.target_id = n.node_id WHERE e.source_id=?"
            params = [node_id]
            if relation:
                q += " AND e.relation=?"
                params.append(relation)
            for row in conn.execute(q, params):
                results.append({"node_id": row[0], "relation": row[1], "weight": row[2],
                                "label": row[3], "type": row[4], "direction": "out"})
        if direction in ("in", "both"):
            q = "SELECT e.source_id, e.relation, e.weight, n.label, n.node_type FROM kg_edges e " \
                "JOIN kg_nodes n ON e.source_id = n.node_id WHERE e.target_id=?"
            params = [node_id]
            if relation:
                q += " AND e.relation=?"
                params.append(relation)
            for row in conn.execute(q, params):
                results.append({"node_id": row[0], "relation": row[1], "weight": row[2],
                                "label": row[3], "type": row[4], "direction": "in"})
        return results

    def query_by_type(self, node_type: str, limit: int = 50) -> list:
        """Find all nodes of a given type"""
        conn = self._get_graph_db()
        rows = conn.execute(
            "SELECT node_id, label, properties FROM kg_nodes WHERE node_type=? ORDER BY updated_at DESC LIMIT ?",
            (node_type, limit)
        ).fetchall()
        return [{"node_id": r[0], "label": r[1], "properties": json.loads(r[2] or "{}")} for r in rows]

    def query_relations(self, relation: str, limit: int = 50) -> list:
        """Find all edges with a given relation"""
        conn = self._get_graph_db()
        rows = conn.execute(
            "SELECT e.source_id, e.target_id, e.weight, s.label, t.label "
            "FROM kg_edges e JOIN kg_nodes s ON e.source_id=s.node_id "
            "JOIN kg_nodes t ON e.target_id=t.node_id "
            "WHERE e.relation=? ORDER BY e.weight DESC LIMIT ?",
            (relation, limit)
        ).fetchall()
        return [{"source": r[0], "target": r[1], "weight": r[2],
                 "source_label": r[3], "target_label": r[4]} for r in rows]

    # ── Explain API ──

    def explain_connection(self, node_a: str, node_b: str, max_depth: int = 3) -> list:
        """Find paths between two nodes (BFS, up to max_depth)"""
        conn = self._get_graph_db()
        visited = {node_a}
        queue = [(node_a, [{"node": node_a}])]
        paths = []

        for depth in range(max_depth):
            next_queue = []
            for current, path in queue:
                # outgoing
                for row in conn.execute(
                    "SELECT target_id, relation FROM kg_edges WHERE source_id=?", (current,)
                ):
                    nid, rel = row
                    if nid in visited:
                        continue
                    new_path = path + [{"relation": rel, "direction": "out"}, {"node": nid}]
                    if nid == node_b:
                        paths.append(new_path)
                        continue
                    visited.add(nid)
                    next_queue.append((nid, new_path))
                # incoming
                for row in conn.execute(
                    "SELECT source_id, relation FROM kg_edges WHERE target_id=?", (current,)
                ):
                    nid, rel = row
                    if nid in visited:
                        continue
                    new_path = path + [{"relation": rel, "direction": "in"}, {"node": nid}]
                    if nid == node_b:
                        paths.append(new_path)
                        continue
                    visited.add(nid)
                    next_queue.append((nid, new_path))
            queue = next_queue
            if paths:
                break

        return paths

    def graph_stats(self) -> dict:
        """Knowledge graph statistics"""
        conn = self._get_graph_db()
        nodes = conn.execute("SELECT COUNT(*) FROM kg_nodes").fetchone()[0]
        edges = conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0]
        by_type = {}
        for row in conn.execute("SELECT node_type, COUNT(*) FROM kg_nodes GROUP BY node_type"):
            by_type[row[0]] = row[1]
        by_relation = {}
        for row in conn.execute("SELECT relation, COUNT(*) FROM kg_edges GROUP BY relation"):
            by_relation[row[0]] = row[1]
        return {"nodes": nodes, "edges": edges, "by_type": by_type, "by_relation": by_relation}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 便捷入口 (兼容旧 memory-index-v6 接口)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def add_entry(self, content: str, source: str = "manual", title: str = "", tags: str = ""):
        conn = self._get_warm_db()
        if not title:
            title = content[:80]
        if self._index_entry(conn, source, title, content, tags):
            conn.commit()
            return True
        return False

    def stats(self) -> dict:
        hot_conn = self._get_hot_db()
        warm_conn = self._get_warm_db()
        sessions = hot_conn.execute("SELECT COUNT(*) FROM session_meta").fetchone()[0]
        hot_msgs = hot_conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        warm_total = warm_conn.execute("SELECT COUNT(*) FROM memory_meta").fetchone()[0]
        by_source = warm_conn.execute("SELECT source, COUNT(*) FROM memory_meta GROUP BY source").fetchall()
        return {
            "hot": {"sessions": sessions, "messages": hot_msgs},
            "warm": {"total": warm_total, "by_source": dict(by_source)},
            "jieba": _HAS_JIEBA,
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 全局单例 + 兼容旧接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_fabric = None

def get_fabric() -> MemoryFabric:
    global _fabric
    if _fabric is None:
        _fabric = MemoryFabric()
    return _fabric

# conversation-buffer-v6 兼容
def append(session_id: str, role: str, content: str):
    get_fabric().append_conversation(session_id, role, content)

def get_context(session_id: str, n: int = 5) -> list:
    return get_fabric().get_history(session_id, n)

def get_history(session_id: str, n: int = 5) -> list:
    return get_fabric().get_history(session_id, n)

def get_context_text(session_id: str, n: int = 5) -> str:
    return get_fabric().get_context_text(session_id, n)

# memory-index-v6 兼容
def search(query: str, top_k: int = 5, category: str = "") -> list:
    return get_fabric().search(query, top_k, category)

def build_index():
    idx, skip = get_fabric().build_index()
    print(f"✅ Memory Fabric 索引构建: {idx} 新条目, {skip} 已存在")

def add_entry(content: str, source: str = "manual", title: str = "", tags: str = ""):
    if get_fabric().add_entry(content, source, title, tags):
        print(f"✅ 已添加: {(title or content)[:60]}")
    else:
        print("⚠️ 已存在，跳过")


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_index()
    elif "--search" in sys.argv:
        idx = sys.argv.index("--search")
        query = " ".join(sys.argv[idx + 1:]) if len(sys.argv) > idx + 1 else ""
        if query:
            results = search(query)
            print(f"🔍 '{query}': {len(results)} 条结果")
            for r in results:
                print(f"  [{r['source']}] {r['title']}")
                print(f"    {r['snippet'][:120]}")
        else:
            print("用法: --search <query>")
    elif "--cleanup" in sys.argv:
        removed, remaining = get_fabric().cleanup_expired()
        print(f"🧹 清理 {removed} 个过期会话, 剩余 {remaining}")
    elif "--stats" in sys.argv:
        s = get_fabric().stats()
        print("📊 Memory Fabric V15 Stats")
        print(f"  Hot: {s['hot']['sessions']} sessions, {s['hot']['messages']} messages")
        print(f"  Warm: {s['warm']['total']} indexed entries")
        for src, cnt in sorted(s['warm'].get('by_source', {}).items(), key=lambda x: -x[1]):
            print(f"    {cnt:4d}  {src}")
        print(f"  jieba: {'✅' if s['jieba'] else '❌'}")
    elif "--graph-stats" in sys.argv:
        gs = get_fabric().graph_stats()
        print("🗑️ Knowledge Graph Stats")
        print(f"  Nodes: {gs['nodes']}")
        print(f"  Edges: {gs['edges']}")
        if gs['by_type']:
            print("  By type:")
            for t, c in sorted(gs['by_type'].items(), key=lambda x: -x[1]):
                print(f"    {t}: {c}")
        if gs['by_relation']:
            print("  By relation:")
            for r, c in sorted(gs['by_relation'].items(), key=lambda x: -x[1]):
                print(f"    {r}: {c}")

    elif "--graph-query" in sys.argv:
        idx = sys.argv.index("--graph-query")
        if len(sys.argv) > idx + 1:
            nid = sys.argv[idx + 1]
            node = get_fabric().query_node(nid)
            if node:
                print(f"Node: {node['node_id']} ({node['type']}): {node['label']}")
                neighbors = get_fabric().query_neighbors(nid)
                if neighbors:
                    print(f"Neighbors ({len(neighbors)}):")
                    for n in neighbors:
                        arrow = "→" if n['direction'] == 'out' else "←"
                        print(f"  {arrow} [{n['relation']}] {n['node_id']} ({n['type']}): {n['label']}")
            else:
                print(f"Node '{nid}' not found")
        else:
            print("用法: --graph-query <node_id>")

    elif "--graph-explain" in sys.argv:
        idx = sys.argv.index("--graph-explain")
        if len(sys.argv) > idx + 2:
            a, b = sys.argv[idx + 1], sys.argv[idx + 2]
            paths = get_fabric().explain_connection(a, b)
            if paths:
                print(f"Found {len(paths)} path(s) from {a} to {b}:")
                for i, path in enumerate(paths):
                    parts = []
                    for step in path:
                        if "node" in step:
                            parts.append(step["node"])
                        elif "relation" in step:
                            arrow = "→" if step["direction"] == "out" else "←"
                            parts.append(f"-[{step['relation']}]{arrow}")
                    print(f"  Path {i+1}: {' '.join(parts)}")
            else:
                print(f"No path found between {a} and {b}")
        else:
            print("用法: --graph-explain <node_a> <node_b>")

    else:
        print("V15 Memory Fabric")
        print("  --build          构建索引")
        print("  --search         搜索记忆")
        print("  --cleanup        清理过期会话")
        print("  --stats          统计信息")
        print("  --graph-stats    知识图谱统计")
        print("  --graph-query    查询节点")
        print("  --graph-explain  解释关联")
