#!/usr/bin/env python3
"""
Knowledge Graph Memory — SQLite-based entity-relation graph for OpenClaw.
Supports: ingest, query, path, neighbors, reinforce, decay, prune, merge, stats, --check.

Version 2.0: Added smart entity type inference and relation normalization.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_DB = os.path.expanduser("~/.openclaw/memory/knowledge-graph.sqlite")
DEFAULT_CONFIG = os.path.expanduser(
    "~/.openclaw/workspace/skills/knowledge-graph-memory/graph-config.yaml"
)
DECAY_LAMBDA = 0.01  # ~230-day half-life

# Load config
CONFIG = {}
CONFIG_PATH = os.path.expanduser(
    "~/.openclaw/workspace/skills/knowledge-graph-memory/graph-config.yaml"
)
if os.path.exists(CONFIG_PATH):
    try:
        import yaml
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            CONFIG = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load config: {e}", file=sys.stderr)

# Type keywords for inference
TYPE_KEYWORDS = CONFIG.get('type_keywords', {
    "person": ["是", "叫", "名", "作者", "用户", "开发者", "创始人", "CEO", "经理"],
    "company": ["公司", "企业", "团队", "组织", "机构", "OpenClaw"],
    "tool": ["工具", "软件", "框架", "库", "API", "语言", "Python", "Java", "JavaScript"],
    "concept": ["策略", "方法", "技术", "概念", "理论", "模式", "系统"],
    "stock": ["股票", "股份", "板块", "SH", "SZ"],
    "event": ["会议", "活动", "事件", "发布"],
    "location": ["城市", "省", "地区", "地址", "北京", "上海", "成都"],
})

# Relation normalization map
RELATION_MAP = {
    "用户": "works_for",
    "开发者": "develops",
    "创始人": "founded",
    "CEO": "leads",
    "经理": "manages",
    "员工": "works_for",
    "使用": "uses",
    "采用": "uses",
    "用": "uses",
    "开发": "develops",
    "属于": "part_of",
    "位于": "located_in",
    "投资": "invests_in",
    "是": "is_a",
    "相关": "related_to",
}


# ── database ────────────────────────────────────────────────────────────────

def get_db(db_path: str = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = CONFIG.get('storage', {}).get('path', DEFAULT_DB)
    db_path = os.path.expanduser(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            properties TEXT DEFAULT '{}',
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            decay_score REAL DEFAULT 1.0
        );
        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);

        CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            target_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            properties TEXT DEFAULT '{}',
            weight REAL DEFAULT 1.0,
            evidence TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rel_source ON relations(source_id);
        CREATE INDEX IF NOT EXISTS idx_rel_target ON relations(target_id);
        CREATE INDEX IF NOT EXISTS idx_rel_type ON relations(type);

        CREATE TABLE IF NOT EXISTS fragments (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT,
            source_id TEXT,
            entities TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()


# ── helpers ─────────────────────────────────────────────────────────────────

def _uid(prefix: str, name: str) -> str:
    return f"{prefix}_{hashlib.sha256(name.encode()).hexdigest()[:12]}"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def infer_entity_type(name: str, context: str = "", pattern_type: str = "default") -> str:
    """
    Infer entity type based on name, context, and pattern.
    
    Args:
        name: Entity name
        context: Full text context
        pattern_type: "is_a" (X 是 Y 的 Z), "uses" (X 使用 Y), or "is_simple" (X 是 Y)
    
    Returns:
        Inferred entity type
    """
    name_lower = name.lower()
    
    # Strategy 1: Check name against keywords
    for etype, keywords in TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return etype
    
    # Strategy 2: Pattern-based inference
    if pattern_type == "is_a":
        # "X 是 Y 的 Z" - infer from the role Z
        if "用户" in name or "开发者" in name or "创始人" in name or "CEO" in name:
            return "person"
        if "公司" in name or "企业" in name or "团队" in name:
            return "company"
        # If this is the role (Z), and it looks like a person role
        if name in ["用户", "开发者", "创始人", "CEO", "经理", "作者"]:
            return "person"
    
    elif pattern_type == "uses":
        # "X 使用 Y" - X is likely person/company
        return "person"  # Default for subject of "uses"
    
    elif pattern_type == "uses_obj":
        # "X 使用 Y" - Y is likely tool/concept
        if len(name) <= 10 and name.isascii():
            return "tool"  # Python, Java, etc.
        return "concept"
    
    # Strategy 3: Context-based
    if "使用" in context or "采用" in context:
        # If name appears as object of "use", likely a tool
        if len(name) <= 10 and not any(c in name for c in "的是了"):
            return "tool"
    
    # Strategy 4: Length and character heuristics
    if len(name) <= 4 and name.isascii():
        # Short ASCII: likely tool/tech (Python, Java, API)
        return "tool"
    
    if len(name) >= 5 and name.isascii():
        # Longer ASCII: could be company or concept
        if any(c.isupper() for c in name):
            return "company"  # CamelCase like OpenClaw
    
    # Default
    return "concept"


def infer_relation_type(raw_text: str) -> str:
    """
    Normalize relation type from raw matched text.
    
    Args:
        raw_text: Raw matched text (e.g., "用户，他使用")
    
    Returns:
        Normalized relation type
    """
    for pattern, rel_type in RELATION_MAP.items():
        if re.search(pattern, raw_text):
            return rel_type
    
    # Default: clean up the raw text
    cleaned = re.sub(r'[的，。、！？]', '', raw_text)
    if len(cleaned) <= 6:
        return cleaned
    
    return "related_to"


# ── CRUD: entities ──────────────────────────────────────────────────────────

def upsert_entity(conn, name: str, etype: str, properties: dict | None = None,
                  confidence: float = 1.0) -> str:
    eid = _uid("e", f"{etype}:{name}")
    now = _now()
    existing = conn.execute("SELECT id FROM entities WHERE id=?", (eid,)).fetchone()
    if existing:
        conn.execute("""
            UPDATE entities SET updated_at=?, access_count=access_count+1,
                   decay_score=1.0, confidence=MAX(confidence,?)
            WHERE id=?
        """, (now, confidence, eid))
    else:
        conn.execute("""
            INSERT INTO entities (id, name, type, properties, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (eid, name, etype, _json_dumps(properties or {}), confidence, now, now))
    conn.commit()
    return eid


def get_entity(conn, name: str = None, eid: str = None) -> dict | None:
    if eid:
        row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
    elif name:
        row = conn.execute(
            "SELECT * FROM entities WHERE name=? COLLATE NOCASE", (name,)
        ).fetchone()
    else:
        return None
    if row:
        # bump access
        conn.execute(
            "UPDATE entities SET access_count=access_count+1, updated_at=? WHERE id=?",
            (_now(), row["id"]),
        )
        conn.commit()
        return dict(row)
    return None


# ── CRUD: relations ─────────────────────────────────────────────────────────

def add_relation(conn, source_id: str, target_id: str, rtype: str,
                 weight: float = 1.0, evidence: str = None, properties: dict | None = None) -> str:
    rid = _uid("r", f"{source_id}:{rtype}:{target_id}")
    now = _now()
    existing = conn.execute("SELECT id FROM relations WHERE id=?", (rid,)).fetchone()
    if existing:
        conn.execute("""
            UPDATE relations SET weight=weight+0.1, updated_at=?, evidence=COALESCE(?,evidence)
            WHERE id=?
        """, (now, evidence, rid))
    else:
        conn.execute("""
            INSERT INTO relations (id, source_id, target_id, type, properties, weight, evidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rid, source_id, target_id, rtype, _json_dumps(properties or {}), weight, evidence, now, now))
    conn.commit()
    return rid


# ── ingest ──────────────────────────────────────────────────────────────────

def llm_extract_entities(text: str, model: str = "qwen3.5-plus") -> dict:
    """
    Use LLM to extract entities and relations from text.
    Returns: {"entities": [...], "relations": [...], "method": "llm"}
    """
    try:
        # Load API config
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if not os.path.exists(config_path):
            return {"entities": [], "relations": [], "llm_error": "Config not found"}
        
        with open(config_path, 'r', encoding='utf-8') as f:
            openclaw_config = json.load(f)
        
        # Get Bailian API config from OpenClaw
        bailian_config = openclaw_config.get('models', {}).get('providers', {}).get('bailian', {})
        api_key = bailian_config.get('apiKey', '')
        base_url_config = bailian_config.get('baseUrl', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        
        # Use OpenClaw's endpoint format: {baseUrl}/chat/completions
        base_url = f"{base_url_config}/chat/completions"
        
        if not api_key:
            return {"entities": [], "relations": [], "llm_error": "No API key"}
        
        # Build prompt
        prompt = f"""从以下文本中提取实体和关系：

文本：{text[:1000]}

输出 JSON 格式（只输出 JSON，不要其他内容）：
{{
  "entities": [
    {{"name": "实体名", "type": "person|company|tool|concept|stock|event|location", "confidence": 0.9}}
  ],
  "relations": [
    {{"source": "实体 A", "target": "实体 B", "type": "works_for|uses|develops|is_a|located_in|invests_in|related_to"}}
  ]
}}"""
        
        # Call Bailian API using OpenAI-compatible format
        import urllib.request
        import ssl
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个实体关系抽取专家。只输出 JSON，不要其他内容。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        req = urllib.request.Request(
            base_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'User-Agent': 'OpenClaw-KG/2.0'
            }
        )
        
        # Disable SSL verification for testing
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Retry logic (3 attempts with increasing timeout)
        last_error = None
        for attempt in range(3):
            try:
                timeout = 30 * (attempt + 1)  # 30s, 60s, 90s
                with urllib.request.urlopen(req, context=context, timeout=timeout) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    # Parse response (OpenAI-compatible format)
                    if 'choices' in result:
                        content = result['choices'][0].get('message', {}).get('content', '')
                        
                        # Extract JSON from response
                        import re
                        json_match = re.search(r'\{[\s\S]*\}', content)
                        if json_match:
                            extracted = json.loads(json_match.group())
                            return {
                                "entities": extracted.get('entities', []),
                                "relations": extracted.get('relations', []),
                                "method": "llm"
                            }
                    
                    last_error = "No valid JSON in response"
                    break  # Don't retry if response is invalid
                    
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if e.code == 401:
                    break  # Don't retry auth errors
            except Exception as api_error:
                last_error = str(api_error)
                continue  # Retry on timeout/network errors
        
        return {"entities": [], "relations": [], "llm_error": f"LLM failed after 3 attempts: {last_error}"}
        
    except Exception as e:
        return {"entities": [], "relations": [], "llm_error": str(e)}


def ingest_text(conn, text: str, source: str = "manual", use_llm: bool = False) -> dict:
    """
    Smart entity/relation extraction with type inference and relation normalization.
    
    Args:
        conn: SQLite connection
        text: Text to ingest
        source: Source label
        use_llm: Whether to use LLM for extraction (default: False, use regex)
    """
    entities_found = []
    relations_found = []
    
    # Try LLM extraction if enabled (hybrid mode always tries LLM first, then falls back to regex)
    extraction_mode = CONFIG.get('extraction', {}).get('mode', 'regex')
    if use_llm and extraction_mode in ['llm', 'hybrid']:
        llm_result = llm_extract_entities(text)
        if llm_result.get('entities') or llm_result.get('relations'):
            # Process LLM results
            for ent in llm_result.get('entities', []):
                eid = upsert_entity(conn, ent['name'], ent['type'], confidence=ent.get('confidence', 0.9))
                entities_found.append({"name": ent['name'], "type": ent['type'], "id": eid})
            for rel in llm_result.get('relations', []):
                src_ent = get_entity(conn, name=rel['source'])
                tgt_ent = get_entity(conn, name=rel['target'])
                if src_ent and tgt_ent:
                    rid = add_relation(conn, src_ent['id'], tgt_ent['id'], rel['type'], evidence=text[:200])
                    relations_found.append({"source": rel['source'], "target": rel['target'], "type": rel['type'], "id": rid})
            # Store fragment and return
            fid = _uid("f", text[:100])
            entity_ids = list({e["id"] for e in entities_found})
            conn.execute("""
                INSERT OR REPLACE INTO fragments (id, content, source, entities, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (fid, text, source, _json_dumps(entity_ids), _now()))
            conn.commit()
            return {
                "entities_extracted": len(entities_found),
                "relations_extracted": len(relations_found),
                "fragment_id": fid,
                "entities": entities_found,
                "relations": relations_found,
                "method": "llm"
            }
    
    # Fall back to regex extraction
    method = "regex"

    # Pattern 1: Chinese quoted terms《xxx》or「xxx」
    for m in re.finditer(r'[《「]([^》」]+)[》」]', text):
        name = m.group(1)
        etype = infer_entity_type(name, text, "quote")
        eid = upsert_entity(conn, name, etype)
        entities_found.append({"name": name, "type": etype, "id": eid})

    # Pattern 2: "X 是 Y 的 Z" (X is Y's Z) - role is 2-6 chars (Chinese or ASCII like CEO)
    for m in re.finditer(r'(\S{1,15})\s*是\s*(\S{1,15})\s*的\s*([A-Za-z\u4e00-\u9fa5]{2,6})', text):
        subj, obj, role = m.group(1), m.group(2), m.group(3)
        
        # Infer types: role (Z) determines subj type
        # If role is "用户", "开发者", etc., subj is person
        if role in ["用户", "开发者", "创始人", "CEO", "经理", "作者", "员工"]:
            subj_type = "person"
        elif role in ["公司", "企业", "团队", "产品", "项目"]:
            subj_type = "company"
        else:
            subj_type = infer_entity_type(subj, text, "is_a")
        
        # Obj type: infer from name
        obj_type = infer_entity_type(obj, text, "is_a_obj")
        
        sid = upsert_entity(conn, subj, subj_type)
        oid = upsert_entity(conn, obj, obj_type)
        
        # Normalize relation type from role
        rel_type = infer_relation_type(role)
        
        rid = add_relation(conn, sid, oid, rel_type, evidence=text[:200])
        entities_found.extend([
            {"name": subj, "type": subj_type, "id": sid},
            {"name": obj, "type": obj_type, "id": oid},
        ])
        relations_found.append({"source": subj, "target": obj, "type": rel_type, "id": rid})

    # Pattern 3: "X 使用/用/采用 Y" (X uses Y) - allow 1-15 chars
    for m in re.finditer(r'(\S{1,15})\s*(?:使用 | 用 | 采用)\s*(\S{1,25})', text):
        subj, obj = m.group(1), m.group(2)
        
        # Skip invalid subjects (e.g., "的用户，他")
        if "的" in subj or "，" in subj:
            continue
        
        # Infer types
        subj_type = infer_entity_type(subj, text, "uses")
        obj_type = infer_entity_type(obj, text, "uses_obj")
        
        sid = upsert_entity(conn, subj, subj_type)
        oid = upsert_entity(conn, obj, obj_type)
        
        rid = add_relation(conn, sid, oid, "uses", evidence=text[:200])
        entities_found.extend([
            {"name": subj, "type": subj_type, "id": sid},
            {"name": obj, "type": obj_type, "id": oid},
        ])
        relations_found.append({"source": subj, "target": obj, "type": "uses", "id": rid})

    # Pattern 4: "X 是 Y" (X is Y) - simple copula without "的"
    for m in re.finditer(r'(\S{1,15})\s*是\s*(\S{1,25})(?:，|。|$|;)', text):
        subj, obj = m.group(1), m.group(2)
        
        # Skip if already matched by pattern 2
        if any(e["name"] == subj for e in entities_found):
            continue
        
        subj_type = infer_entity_type(subj, text, "is_simple")
        obj_type = infer_entity_type(obj, text, "is_simple_obj")
        
        sid = upsert_entity(conn, subj, subj_type)
        oid = upsert_entity(conn, obj, obj_type)
        
        rid = add_relation(conn, sid, oid, "is_a", evidence=text[:200])
        entities_found.extend([
            {"name": subj, "type": subj_type, "id": sid},
            {"name": obj, "type": obj_type, "id": oid},
        ])
        relations_found.append({"source": subj, "target": obj, "type": "is_a", "id": rid})

    # Pattern 5: "X 投资 (了) Y" (X invests in Y) - no spaces around 投资
    for m in re.finditer(r'([\u4e00-\u9fa5]{1,15})\s*投资 (?:了)?\s*([\u4e00-\u9fa5A-Za-z]{1,25})', text):
        subj, obj = m.group(1), m.group(2)
        
        subj_type = infer_entity_type(subj, text, "invests")
        obj_type = infer_entity_type(obj, text, "invests_obj")
        
        sid = upsert_entity(conn, subj, subj_type)
        oid = upsert_entity(conn, obj, obj_type)
        
        rid = add_relation(conn, sid, oid, "invests_in", evidence=text[:200])
        entities_found.extend([
            {"name": subj, "type": subj_type, "id": sid},
            {"name": obj, "type": obj_type, "id": oid},
        ])
        relations_found.append({"source": subj, "target": obj, "type": "invests_in", "id": rid})

    # Filter out low-quality entities
    def is_valid_entity(name: str, etype: str) -> bool:
        if len(name) < 2:
            return False
        # Blacklist common false positives
        if name in ["的用户", "他", "她", "它", "这个", "那个", "一个"]:
            return False
        # Filter entities containing "的" or "，" (likely parsing errors)
        if "的" in name or "，" in name or "。" in name:
            return False
        if etype == "concept" and any(x in name for x in ["了", "是"]):
            return False
        return True
    
    entities_found = [e for e in entities_found if is_valid_entity(e["name"], e["type"])]
    
    # Filter relations based on valid entities
    valid_entity_names = {e["name"] for e in entities_found}
    relations_found = [r for r in relations_found 
                       if r["source"] in valid_entity_names and r["target"] in valid_entity_names]

    # Store fragment
    fid = _uid("f", text[:100])
    entity_ids = list({e["id"] for e in entities_found})
    conn.execute("""
        INSERT OR REPLACE INTO fragments (id, content, source, entities, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (fid, text, source, _json_dumps(entity_ids), _now()))
    conn.commit()

    return {
        "entities_extracted": len(entities_found),
        "relations_extracted": len(relations_found),
        "fragment_id": fid,
        "entities": entities_found,
        "relations": relations_found,
    }


def ingest_file(conn, filepath: str) -> dict:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        return ingest_text(conn, text, source=f"file:{filepath}")
    except Exception as e:
        return {"error": str(e), "filepath": filepath}


# ── query ───────────────────────────────────────────────────────────────────

def query_entity(conn, name: str) -> dict | None:
    ent = get_entity(conn, name=name)
    if not ent:
        return None
    rels_out = conn.execute("""
        SELECT r.*, e.name as target_name FROM relations r
        JOIN entities e ON r.target_id=e.id WHERE r.source_id=?
    """, (ent["id"],)).fetchall()
    rels_in = conn.execute("""
        SELECT r.*, e.name as source_name FROM relations r
        JOIN entities e ON r.source_id=e.id WHERE r.target_id=?
    """, (ent["id"],)).fetchall()
    return {
        "entity": dict(ent),
        "outgoing": [dict(r) for r in rels_out],
        "incoming": [dict(r) for r in rels_in],
    }


def query_relation(conn, name: str, rtype: str) -> list:
    ent = get_entity(conn, name=name)
    if not ent:
        return []
    rows = conn.execute("""
        SELECT r.*, e.name as target_name FROM relations r
        JOIN entities e ON r.target_id=e.id
        WHERE r.source_id=? AND r.type=?
    """, (ent["id"], rtype)).fetchall()
    return [dict(r) for r in rows]


def find_path(conn, from_name: str, to_name: str, max_depth: int = 4) -> list | None:
    """BFS shortest path between two entities."""
    e_from = get_entity(conn, name=from_name)
    e_to = get_entity(conn, name=to_name)
    if not e_from or not e_to:
        return None

    visited = {e_from["id"]}
    queue = [(e_from["id"], [e_from["name"]])]

    for _ in range(max_depth):
        next_queue = []
        for eid, path in queue:
            neighbors = conn.execute("""
                SELECT r.type, r.target_id, e.name FROM relations r
                JOIN entities e ON r.target_id=e.id WHERE r.source_id=?
                UNION
                SELECT r.type, r.source_id, e.name FROM relations r
                JOIN entities e ON r.source_id=e.id WHERE r.target_id=?
            """, (eid, eid)).fetchall()
            for rel_type, nid, nname in neighbors:
                if nid == e_to["id"]:
                    return path + [f"--{rel_type}-->", nname]
                if nid not in visited:
                    visited.add(nid)
                    next_queue.append((nid, path + [f"--{rel_type}-->", nname]))
        queue = next_queue
    return None


def get_neighbors(conn, name: str, depth: int = 1) -> dict:
    ent = get_entity(conn, name=name)
    if not ent:
        return {"error": f"Entity '{name}' not found"}

    result = {"center": ent["name"], "neighbors": []}
    visited = {ent["id"]}
    current_layer = [ent["id"]]

    for d in range(depth):
        next_layer = []
        for eid in current_layer:
            rows = conn.execute("""
                SELECT r.type as rel_type, e.id, e.name, e.type as etype, 'out' as direction
                FROM relations r JOIN entities e ON r.target_id=e.id WHERE r.source_id=?
                UNION
                SELECT r.type as rel_type, e.id, e.name, e.type as etype, 'in' as direction
                FROM relations r JOIN entities e ON r.source_id=e.id WHERE r.target_id=?
            """, (eid, eid)).fetchall()
            for row in rows:
                if row["id"] not in visited:
                    visited.add(row["id"])
                    next_layer.append(row["id"])
                    result["neighbors"].append({
                        "name": row["name"],
                        "type": row["etype"],
                        "relation": row["rel_type"],
                        "direction": row["direction"],
                        "depth": d + 1,
                    })
        current_layer = next_layer
    return result


# ── reinforce / decay / prune ───────────────────────────────────────────────

def reinforce(conn, name: str, reason: str = ""):
    ent = get_entity(conn, name=name)
    if not ent:
        print(json.dumps({"error": f"Entity '{name}' not found"}))
        return
    conn.execute("""
        UPDATE entities SET decay_score=1.0, access_count=access_count+1, updated_at=?
        WHERE id=?
    """, (_now(), ent["id"]))
    conn.commit()
    print(json.dumps({"reinforced": name, "reason": reason, "new_decay_score": 1.0}))


def run_decay(conn, lam: float = None):
    if lam is None:
        lam = CONFIG.get('decay', {}).get('lambda', DECAY_LAMBDA)
    now = datetime.now()
    rows = conn.execute("SELECT id, updated_at, decay_score FROM entities").fetchall()
    updated = 0
    for row in rows:
        last = datetime.fromisoformat(row["updated_at"])
        days = (now - last).total_seconds() / 86400
        new_score = row["decay_score"] * math.exp(-lam * days)
        conn.execute("UPDATE entities SET decay_score=? WHERE id=?", (round(new_score, 6), row["id"]))
        updated += 1
    conn.commit()
    print(json.dumps({"decayed_entities": updated, "lambda": lam}))


def prune(conn, threshold: float = None):
    if threshold is None:
        threshold = CONFIG.get('decay', {}).get('prune_threshold', 0.05)
    rows = conn.execute(
        "SELECT id, name, decay_score FROM entities WHERE decay_score < ?", (threshold,)
    ).fetchall()
    pruned = []
    for row in rows:
        conn.execute("DELETE FROM entities WHERE id=?", (row["id"],))
        pruned.append({"name": row["name"], "decay_score": row["decay_score"]})
    conn.commit()
    print(json.dumps({"pruned": len(pruned), "entities": pruned}))


# ── merge / dedup ───────────────────────────────────────────────────────────

def find_duplicates(conn) -> list:
    rows = conn.execute("""
        SELECT name, COUNT(*) as cnt FROM entities
        GROUP BY LOWER(name) HAVING cnt > 1
    """).fetchall()
    return [dict(r) for r in rows]


def merge_entities(conn, keep_id: str, remove_id: str):
    conn.execute("UPDATE relations SET source_id=? WHERE source_id=?", (keep_id, remove_id))
    conn.execute("UPDATE relations SET target_id=? WHERE target_id=?", (keep_id, remove_id))
    conn.execute("DELETE FROM entities WHERE id=?", (remove_id,))
    conn.commit()


# ── stats ───────────────────────────────────────────────────────────────────

def stats(conn) -> dict:
    e_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    r_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
    f_count = conn.execute("SELECT COUNT(*) FROM fragments").fetchone()[0]
    avg_decay = conn.execute("SELECT AVG(decay_score) FROM entities").fetchone()[0] or 0

    type_dist = conn.execute(
        "SELECT type, COUNT(*) as cnt FROM entities GROUP BY type ORDER BY cnt DESC"
    ).fetchall()

    most_connected = conn.execute("""
        SELECT e.name, (
            (SELECT COUNT(*) FROM relations WHERE source_id=e.id) +
            (SELECT COUNT(*) FROM relations WHERE target_id=e.id)
        ) as connections
        FROM entities e ORDER BY connections DESC LIMIT 5
    """).fetchall()

    most_accessed = conn.execute(
        "SELECT name, access_count FROM entities ORDER BY access_count DESC LIMIT 5"
    ).fetchall()

    return {
        "entities": e_count,
        "relations": r_count,
        "fragments": f_count,
        "avg_decay_score": round(avg_decay, 4),
        "type_distribution": {r["type"]: r["cnt"] for r in type_dist},
        "most_connected": [{"name": r["name"], "connections": r[1]} for r in most_connected],
        "most_accessed": [{"name": r["name"], "access_count": r["access_count"]} for r in most_accessed],
    }


# ── health check ────────────────────────────────────────────────────────────

def health_check(db_path: str = None) -> dict:
    checks = []

    # Check config
    if os.path.exists(CONFIG_PATH):
        checks.append({"name": "config", "type": "file", "status": "ok", "path": CONFIG_PATH})
    else:
        checks.append({"name": "config", "type": "file", "status": "warn", "message": "Config file not found"})

    # Check SQLite writable
    try:
        if db_path is None:
            db_path = CONFIG.get('storage', {}).get('path', DEFAULT_DB)
        conn = get_db(db_path)
        conn.execute("SELECT 1")
        checks.append({"name": "sqlite_db", "type": "file", "status": "ok", "path": db_path})
    except Exception as e:
        checks.append({"name": "sqlite_db", "type": "file", "status": "fail", "message": str(e)})
        return _check_result(checks)

    # Check entity count
    s = stats(conn)
    checks.append({
        "name": "data",
        "type": "env",
        "status": "ok",
        "message": f"{s['entities']} entities, {s['relations']} relations, {s['fragments']} fragments",
    })

    conn.close()
    return _check_result(checks)


def _check_result(checks: list) -> dict:
    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {
        "skill": "knowledge-graph-memory",
        "version": "2.0.0",
        "status": overall,
        "checks": checks,
        "timestamp": _now(),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph Memory CLI")
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--check", action="store_true", help="Health check")

    sub = parser.add_subparsers(dest="command")

    p_ingest = sub.add_parser("ingest", help="Ingest text or file")
    p_ingest.add_argument("--text", help="Text to ingest")
    p_ingest.add_argument("--file", help="File to ingest")

    p_query = sub.add_parser("query", help="Query entity or relation")
    p_query.add_argument("--entity", help="Entity name")
    p_query.add_argument("--relation", nargs=2, metavar=("NAME", "TYPE"), help="Query relations")

    p_path = sub.add_parser("path", help="Find path between entities")
    p_path.add_argument("--from", dest="from_name", required=True)
    p_path.add_argument("--to", dest="to_name", required=True)
    p_path.add_argument("--depth", type=int, default=4)

    p_neigh = sub.add_parser("neighbors", help="Get neighbors of entity")
    p_neigh.add_argument("--entity", required=True)
    p_neigh.add_argument("--depth", type=int, default=1)

    p_reinforce = sub.add_parser("reinforce", help="Reinforce entity")
    p_reinforce.add_argument("--entity", required=True)
    p_reinforce.add_argument("--reason", default="")

    sub.add_parser("decay", help="Run decay on all entities")

    p_prune = sub.add_parser("prune", help="Prune low-score entities")
    p_prune.add_argument("--threshold", type=float, default=None)

    sub.add_parser("find-duplicates", help="Find duplicate entities")

    p_merge = sub.add_parser("merge", help="Merge entities")
    p_merge.add_argument("--ids", nargs=2, required=True, metavar=("KEEP", "REMOVE"))

    sub.add_parser("stats", help="Show graph statistics")

    args = parser.parse_args()

    if args.check:
        result = health_check(args.db)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    conn = get_db(args.db)

    if args.command == "ingest":
        if args.text:
            result = ingest_text(conn, args.text)
        elif args.file:
            result = ingest_file(conn, args.file)
        else:
            print('{"error": "Provide --text or --file"}')
            sys.exit(1)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "query":
        if args.entity:
            result = query_entity(conn, args.entity)
            print(json.dumps(result, indent=2, ensure_ascii=False) if result
                  else json.dumps({"error": f"Entity '{args.entity}' not found"}))
        elif args.relation:
            result = query_relation(conn, args.relation[0], args.relation[1])
            print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "path":
        result = find_path(conn, args.from_name, args.to_name, args.depth)
        print(json.dumps({"path": result} if result else {"path": None, "message": "No path found"},
                         indent=2, ensure_ascii=False))

    elif args.command == "neighbors":
        result = get_neighbors(conn, args.entity, args.depth)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "reinforce":
        reinforce(conn, args.entity, args.reason)

    elif args.command == "decay":
        run_decay(conn)

    elif args.command == "prune":
        prune(conn, args.threshold)

    elif args.command == "find-duplicates":
        result = find_duplicates(conn)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "merge":
        merge_entities(conn, args.ids[0], args.ids[1])
        print(json.dumps({"merged": args.ids[0], "removed": args.ids[1]}))

    elif args.command == "stats":
        result = stats(conn)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    conn.close()


if __name__ == "__main__":
    main()
