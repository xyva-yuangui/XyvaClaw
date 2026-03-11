#!/usr/bin/env python3
"""
Knowledge Graph - Natural Language Query Interface

Allows querying the knowledge graph using natural language.

Usage:
    python3 kg_query.py "圆规和 OpenClaw 有什么关系？"
    python3 kg_query.py "找出所有使用 Python 的人"
    python3 kg_query.py "圆规的知识图谱"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Add kg.py to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from kg import get_db, query_entity, find_path, get_neighbors, stats


def parse_query(query: str) -> dict:
    """
    Parse natural language query into structured query.
    
    Args:
        query: Natural language query
    
    Returns:
        {
            "type": "entity_query|relation_query|path_query|stats|unknown",
            "entities": [str],
            "relation_type": str,
            "intent": str
        }
    """
    query = query.strip()
    
    # Pattern 1: "X 和 Y 有什么关系" / "X 和 Y 的关系"
    match = re.search(r'(.+)\s*和\s*(.+?)\s*有什么关系', query)
    if not match:
        match = re.search(r'(.+)\s*和\s*(.+?)\s*的关系', query)
    if match:
        return {
            "type": "path_query",
            "entities": [match.group(1).strip(), match.group(2).strip()],
            "intent": "find_relationship"
        }
    
    # Pattern 2: "找出所有使用 X 的人" / "谁使用 X"
    match = re.search(r'(?:找出所有 | 谁) 使用 (.+?)(?:的人)?$', query)
    if match:
        return {
            "type": "relation_query",
            "entities": [match.group(1).strip()],
            "relation_type": "uses",
            "intent": "find_users_of_tool"
        }
    
    # Pattern 3: "X 的知识图谱" / "X 的相关信息" / "X 的所有关系"
    match = re.search(r'(.+?)\s*的\s*(?:知识图谱 | 相关信息 | 所有关系)', query)
    if not match:
        # Also try without "的"
        match = re.search(r'^(.+?)\s*知识图谱\s*$', query)
    if match:
        return {
            "type": "entity_query",
            "entities": [match.group(1).strip()],
            "intent": "entity_details"
        }
    
    # Pattern 4: "统计" / "概览"
    if any(kw in query for kw in ["统计", "概览", "有多少实体", "图谱大小"]):
        return {
            "type": "stats",
            "entities": [],
            "intent": "graph_stats"
        }
    
    # Pattern 5: "X 是谁" / "X 是什么"
    match = re.search(r'(.+?) 是 (?:谁 | 什么)', query)
    if match:
        return {
            "type": "entity_query",
            "entities": [match.group(1).strip()],
            "intent": "entity_type"
        }
    
    # Default: try as entity name
    return {
        "type": "entity_query",
        "entities": [query],
        "intent": "entity_lookup"
    }


def execute_query(parsed: dict, conn) -> dict:
    """
    Execute parsed query against the knowledge graph.
    
    Args:
        parsed: Parsed query dict
        conn: SQLite connection
    
    Returns:
        Query result dict
    """
    query_type = parsed["type"]
    
    if query_type == "path_query":
        entities = parsed["entities"]
        if len(entities) >= 2:
            path = find_path(conn, entities[0], entities[1])
            return {
                "answer": format_path_answer(entities[0], entities[1], path),
                "data": {"path": path}
            }
    
    elif query_type == "relation_query":
        entity = parsed["entities"][0]
        rel_type = parsed.get("relation_type", "uses")
        
        # Find all entities that have this relation to the target
        results = conn.execute("""
            SELECT e1.name, e1.type
            FROM relations r
            JOIN entities e1 ON r.source_id = e1.id
            JOIN entities e2 ON r.target_id = e2.id
            WHERE e2.name = ? AND r.type = ?
        """, (entity, rel_type)).fetchall()
        
        return {
            "answer": format_relation_answer(entity, rel_type, results),
            "data": {"results": [{"name": r[0], "type": r[1]} for r in results]}
        }
    
    elif query_type == "entity_query":
        entity_name = parsed["entities"][0]
        entity_data = query_entity(conn, entity_name)
        
        if not entity_data:
            return {
                "answer": f"未找到实体 '{entity_name}'",
                "data": None
            }
        
        if parsed["intent"] == "entity_type":
            return {
                "answer": f"{entity_name} 是 {entity_data['entity']['type']}",
                "data": entity_data
            }
        
        # Default: return full entity details
        return {
            "answer": format_entity_answer(entity_data),
            "data": entity_data
        }
    
    elif query_type == "stats":
        s = stats(conn)
        return {
            "answer": format_stats_answer(s),
            "data": s
        }
    
    return {
        "answer": "抱歉，我不理解这个问题。请尝试：'X 和 Y 有什么关系'、'谁使用 X'、'X 的知识图谱'",
        "data": None
    }


def format_path_answer(entity_a: str, entity_b: str, path: list) -> str:
    """Format path query answer."""
    if not path:
        return f"{entity_a} 和 {entity_b} 之间没有直接连接"
    
    path_str = " → ".join(path)
    return f"{entity_a} 和 {entity_b} 的关系路径：\n{path_str}"


def format_relation_answer(entity: str, rel_type: str, results: list) -> str:
    """Format relation query answer."""
    if not results:
        return f"没有找到使用 {entity} 的实体"
    
    names = [f"{r['name']}({r['type']})" for r in results[:10]]
    return f"使用 {entity} 的实体有：\n" + "\n".join(f"  - {n}" for n in names)


def format_entity_answer(entity_data: dict) -> str:
    """Format entity query answer."""
    entity = entity_data["entity"]
    lines = [
        f"实体：{entity['name']}",
        f"类型：{entity['type']}",
        f"置信度：{entity['confidence']}",
        "",
        "关系:",
    ]
    
    for rel in entity_data.get("outgoing", [])[:5]:
        lines.append(f"  → {rel['type']} → {rel['target_name']}")
    
    for rel in entity_data.get("incoming", [])[:5]:
        lines.append(f"  ← {rel['type']} ← {rel['source_name']}")
    
    if not entity_data.get("outgoing") and not entity_data.get("incoming"):
        lines.append("  (无关系)")
    
    return "\n".join(lines)


def format_stats_answer(s: dict) -> str:
    """Format stats answer."""
    lines = [
        "知识图谱统计:",
        f"  实体总数：{s['entities']}",
        f"  关系总数：{s['relations']}",
        f"  知识片段：{s['fragments']}",
        f"  平均衰减分数：{s['avg_decay_score']}",
        "",
        "类型分布:",
    ]
    
    for etype, count in s['type_distribution'].items():
        lines.append(f"  {etype}: {count}")
    
    return "\n".join(lines)


def natural_language_query(query: str, db_path: str = None) -> dict:
    """
    Main entry point for natural language queries.
    
    Args:
        query: Natural language query
        db_path: Database path
    
    Returns:
        {
            "query": str,
            "parsed": dict,
            "answer": str,
            "data": dict
        }
    """
    conn = get_db(db_path)
    try:
        parsed = parse_query(query)
        result = execute_query(parsed, conn)
        return {
            "query": query,
            "parsed": parsed,
            "answer": result["answer"],
            "data": result["data"]
        }
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph Natural Language Query")
    parser.add_argument("query", nargs="?", help="Natural language query")
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.query:
        print("Usage: python3 kg_query.py '查询语句'")
        print("\n示例:")
        print("  python3 kg_query.py '圆规和 OpenClaw 有什么关系？'")
        print("  python3 kg_query.py '谁使用 Python？'")
        print("  python3 kg_query.py '圆规的知识图谱'")
        print("  python3 kg_query.py '统计'")
        sys.exit(0)
    
    result = natural_language_query(args.query, args.db)
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result["answer"])


if __name__ == "__main__":
    main()
