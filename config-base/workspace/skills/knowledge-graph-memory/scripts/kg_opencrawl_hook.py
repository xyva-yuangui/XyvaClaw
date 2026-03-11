#!/usr/bin/env python3
"""
Knowledge Graph Memory - OpenClaw Integration Hook

This script provides hooks for OpenClaw to automatically ingest conversation
data into the knowledge graph at the end of each session.

Usage:
    from kg_opencrawl_hook import on_session_end, on_session_start

Integration points:
    1. Session end: Call on_session_end(session_data)
    2. Session start: Call on_session_start(session_data) for context retrieval
    3. During reasoning: Call query_knowledge(topic) for auxiliary knowledge
"""

import json
import os
import sys
from pathlib import Path

# Add kg.py to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from kg import get_db, ingest_text, query_entity, find_path, get_neighbors, stats

KG_CONFIG_PATH = SCRIPT_DIR.parent / "graph-config.yaml"


def load_config():
    """Load knowledge graph config."""
    try:
        import yaml
        with open(KG_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def on_session_start(session_data: dict) -> dict:
    """
    Called at session start. Retrieves relevant knowledge from the graph.
    
    Args:
        session_data: {
            "session_id": str,
            "user_id": str,
            "initial_message": str,
            "topics": [str]  # Optional: pre-extracted topics
        }
    
    Returns:
        {
            "relevant_knowledge": [...],
            "related_entities": [...],
            "suggested_context": str
        }
    """
    config = load_config()
    if not config.get('integration', {}).get('auto_query', False):
        return {"relevant_knowledge": [], "message": "Auto-query disabled"}
    
    conn = get_db()
    results = {
        "relevant_knowledge": [],
        "related_entities": [],
        "suggested_context": ""
    }
    
    # Extract topics from initial message
    topics = session_data.get('topics', [])
    if not topics and session_data.get('initial_message'):
        # Simple keyword extraction (first 5 nouns)
        # In production, this would use NLP
        topics = session_data['initial_message'].split()[:5]
    
    # Query knowledge for each topic
    for topic in topics[:3]:  # Limit to 3 topics
        entity_data = query_entity(conn, topic)
        if entity_data:
            results["related_entities"].append({
                "name": entity_data["entity"]["name"],
                "type": entity_data["entity"]["type"],
                "relations": {
                    "outgoing": len(entity_data.get("outgoing", [])),
                    "incoming": len(entity_data.get("incoming", []))
                }
            })
            
            # Build context suggestion
            for rel in entity_data.get("outgoing", [])[:2]:
                results["relevant_knowledge"].append({
                    "fact": f"{topic} {rel['type']} {rel['target_name']}",
                    "confidence": "high"
                })
    
    conn.close()
    
    # Generate suggested context
    if results["relevant_knowledge"]:
        facts = [k["fact"] for k in results["relevant_knowledge"][:3]]
        results["suggested_context"] = "相关知识：" + "；".join(facts)
    
    return results


def on_session_end(session_data: dict) -> dict:
    """
    Called at session end. Ingests conversation into the knowledge graph.
    
    Args:
        session_data: {
            "session_id": str,
            "user_id": str,
            "messages": [
                {"role": "user|assistant", "content": str, "timestamp": str}
            ],
            "summary": str,  # Optional: session summary
            "topics": [str]  # Optional: extracted topics
        }
    
    Returns:
        {
            "entities_extracted": int,
            "relations_extracted": int,
            "fragments_stored": int,
            "status": "success|partial|failed",
            "error": str  # Only if failed
        }
    """
    config = load_config()
    if not config.get('extraction', {}).get('auto_ingest', False):
        return {"status": "skipped", "message": "Auto-ingest disabled"}
    
    conn = get_db()
    result = {
        "entities_extracted": 0,
        "relations_extracted": 0,
        "fragments_stored": 0,
        "status": "success"
    }
    
    try:
        # Ingest session summary if available
        if session_data.get('summary'):
            ingest_result = ingest_text(
                conn, 
                session_data['summary'], 
                source=f"session_summary:{session_data['session_id']}"
            )
            result["entities_extracted"] += ingest_result.get("entities_extracted", 0)
            result["relations_extracted"] += ingest_result.get("relations_extracted", 0)
            result["fragments_stored"] += 1
        
        # Ingest key messages (user messages only, limit to 10)
        messages = session_data.get('messages', [])
        user_messages = [m for m in messages if m.get('role') == 'user']
        
        for msg in user_messages[-10:]:  # Last 10 user messages
            content = msg.get('content', '')
            if len(content) > 20:  # Skip very short messages
                ingest_result = ingest_text(
                    conn,
                    content,
                    source=f"session:{session_data['session_id']}"
                )
                result["entities_extracted"] += ingest_result.get("entities_extracted", 0)
                result["relations_extracted"] += ingest_result.get("relations_extracted", 0)
                result["fragments_stored"] += 1
        
        # Run decay periodically (every 10 sessions)
        # This is a simple heuristic; in production, use cron
        session_count = int(stats(conn).get('fragments', 0))
        if session_count % 10 == 0:
            from kg import run_decay
            run_decay(conn)
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
    finally:
        conn.close()
    
    return result


def query_knowledge(topic: str, depth: int = 1) -> dict:
    """
    Query knowledge graph for a specific topic.
    
    Args:
        topic: Entity name to query
        depth: Neighborhood depth (1-3)
    
    Returns:
        {
            "entity": {...},
            "neighbors": [...],
            "facts": [...]
        }
    """
    conn = get_db()
    try:
        entity_data = query_entity(conn, topic)
        if not entity_data:
            return {"error": f"Entity '{topic}' not found"}
        
        neighbors = get_neighbors(conn, topic, depth)
        
        # Build facts
        facts = []
        for rel in entity_data.get("outgoing", []):
            facts.append(f"{topic} {rel['type']} {rel['target_name']}")
        for rel in entity_data.get("incoming", []):
            facts.append(f"{rel['source_name']} {rel['type']} {topic}")
        
        return {
            "entity": entity_data["entity"],
            "neighbors": neighbors.get("neighbors", []),
            "facts": facts
        }
    finally:
        conn.close()


def find_connections(entity_a: str, entity_b: str) -> dict:
    """
    Find connections between two entities.
    
    Args:
        entity_a: First entity name
        entity_b: Second entity name
    
    Returns:
        {
            "path": [...],  # Path from A to B
            "exists": bool
        }
    """
    conn = get_db()
    try:
        path = find_path(conn, entity_a, entity_b)
        return {
            "path": path,
            "exists": path is not None
        }
    finally:
        conn.close()


# CLI for testing
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KG OpenClaw Hook CLI")
    parser.add_argument("--test-ingest", type=str, help="Test ingest with text")
    parser.add_argument("--test-ingest-file", type=str, help="Test ingest with session file")
    parser.add_argument("--test-query", type=str, help="Test query with entity name")
    
    args = parser.parse_args()
    
    if args.test_ingest:
        result = on_session_end({
            "session_id": "test",
            "user_id": "test",
            "messages": [{"role": "user", "content": args.test_ingest}],
            "summary": args.test_ingest
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.test_ingest_file:
        # Load session data from file
        with open(args.test_ingest_file.strip('"'), 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        result = on_session_end(session_data)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.test_query:
        result = query_knowledge(args.test_query)
        print(json.dumps(result, indent=2, ensure_ascii=False))
