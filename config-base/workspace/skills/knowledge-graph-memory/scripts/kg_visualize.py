#!/usr/bin/env python3
"""
Knowledge Graph Visualization

Generates visual representations of the knowledge graph:
1. Network graph (HTML interactive)
2. Entity relationship diagram (PNG)
3. Text-based summary

Usage:
    python3 kg_visualize.py --output graph.html
    python3 kg_visualize.py --output graph.png --entity "圆规"
    python3 kg_visualize.py --summary
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add kg.py to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from kg import get_db, stats, get_neighbors, find_path

# Try to import visualization libraries
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False


def generate_html_graph(db_path: str = None, output_path: str = "graph.html", 
                        max_entities: int = 100) -> str:
    """
    Generate interactive HTML graph using pyvis.
    
    Args:
        db_path: Path to SQLite database
        output_path: Output HTML file path
        max_entities: Maximum entities to include
    
    Returns:
        Output file path
    """
    if not HAS_PYVIS:
        return "pyvis not installed. Run: pip3 install pyvis"
    
    conn = get_db(db_path)
    
    # Get all entities and relations
    entities = conn.execute("SELECT id, name, type FROM entities LIMIT ?", (max_entities,)).fetchall()
    relations = conn.execute("""
        SELECT r.source_id, r.target_id, r.type, e1.name as source_name, e2.name as target_name
        FROM relations r
        JOIN entities e1 ON r.source_id = e1.id
        JOIN entities e2 ON r.target_id = e2.id
    """).fetchall()
    
    conn.close()
    
    # Create network
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    
    # Color mapping for entity types
    type_colors = {
        "person": "#FF6B6B",
        "company": "#4ECDC4",
        "tool": "#45B7D1",
        "concept": "#96CEB4",
        "location": "#FFEAA7",
        "stock": "#DFE6E9",
        "event": "#FAB1A0"
    }
    
    # Add nodes
    entity_map = {}
    for eid, name, etype in entities:
        color = type_colors.get(etype, "#95A5A6")
        net.add_node(eid, label=name, title=f"{name} ({etype})", color=color, size=20)
        entity_map[eid] = {"name": name, "type": etype}
    
    # Add edges
    for src_id, tgt_id, rel_type, src_name, tgt_name in relations:
        if src_id in entity_map and tgt_id in entity_map:
            net.add_edge(src_id, tgt_id, label=rel_type, title=rel_type)
    
    # Enable physics
    net.set_options("""
    {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "maxVelocity": 50,
        "solver": "forceAtlas2Based",
        "timestep": 0.35
      }
    }
    """)
    
    # Write output
    output_path = os.path.expanduser(output_path)
    net.save_graph(output_path)
    
    return output_path


def generate_text_summary(db_path: str = None) -> str:
    """
    Generate text-based graph summary.
    
    Returns:
        Formatted text summary
    """
    conn = get_db(db_path)
    
    # Get stats
    s = stats(conn)
    
    # Get top entities
    top_entities = conn.execute("""
        SELECT e.name, e.type, 
               (SELECT COUNT(*) FROM relations WHERE source_id=e.id) +
               (SELECT COUNT(*) FROM relations WHERE target_id=e.id) as connections
        FROM entities e
        ORDER BY connections DESC
        LIMIT 10
    """).fetchall()
    
    # Get recent fragments
    recent = conn.execute("""
        SELECT content, created_at FROM fragments
        ORDER BY created_at DESC
        LIMIT 5
    """).fetchall()
    
    conn.close()
    
    # Build summary
    lines = [
        "=" * 60,
        "知识图谱概览",
        "=" * 60,
        "",
        f"实体总数：{s['entities']}",
        f"关系总数：{s['relations']}",
        f"知识片段：{s['fragments']}",
        f"平均衰减分数：{s['avg_decay_score']}",
        "",
        "实体类型分布:",
    ]
    
    for etype, count in s['type_distribution'].items():
        lines.append(f"  {etype}: {count}")
    
    lines.extend([
        "",
        "最连接的实体:",
    ])
    
    for ent in top_entities:
        lines.append(f"  {ent['name']} ({ent['type']}): {ent['connections']} 个连接")
    
    lines.extend([
        "",
        "最近摄入:",
    ])
    
    for frag in recent:
        content = frag['content'][:50] + "..." if len(frag['content']) > 50 else frag['content']
        lines.append(f"  - {content}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_entity_report(db_path: str = None, entity_name: str = None, 
                           output_path: str = None) -> str:
    """
    Generate detailed report for a specific entity.
    
    Args:
        db_path: Database path
        entity_name: Entity name to report on
        output_path: Optional output file path
    
    Returns:
        Report text
    """
    conn = get_db(db_path)
    
    # Get entity
    entity = conn.execute("SELECT * FROM entities WHERE name=? COLLATE NOCASE", 
                          (entity_name,)).fetchone()
    
    if not entity:
        conn.close()
        return f"Entity '{entity_name}' not found"
    
    # Get relations
    outgoing = conn.execute("""
        SELECT r.type, e.name as target_name, e.type as target_type
        FROM relations r
        JOIN entities e ON r.target_id = e.id
        WHERE r.source_id = ?
    """, (entity['id'],)).fetchall()
    
    incoming = conn.execute("""
        SELECT r.type, e.name as source_name, e.type as source_type
        FROM relations r
        JOIN entities e ON r.source_id = e.id
        WHERE r.target_id = ?
    """, (entity['id'],)).fetchall()
    
    # Get neighbors
    neighbors = get_neighbors(conn, entity_name, depth=2)
    
    conn.close()
    
    # Build report
    lines = [
        "=" * 60,
        f"实体报告：{entity['name']}",
        "=" * 60,
        "",
        f"类型：{entity['type']}",
        f"置信度：{entity['confidence']}",
        f"访问次数：{entity['access_count']}",
        f"衰减分数：{entity['decay_score']}",
        f"创建时间：{entity['created_at']}",
        "",
        " outgoing 关系:",
    ]
    
    for rel in outgoing:
        lines.append(f"  --{rel['type']}--> {rel['target_name']} ({rel['target_type']})")
    
    if not outgoing:
        lines.append("  (无)")
    
    lines.extend([
        "",
        "incoming 关系:",
    ])
    
    for rel in incoming:
        lines.append(f"  <--{rel['type']}-- {rel['source_name']} ({rel['source_type']})")
    
    if not incoming:
        lines.append("  (无)")
    
    lines.extend([
        "",
        "二度邻居:",
    ])
    
    for neighbor in neighbors.get('neighbors', [])[:10]:
        lines.append(f"  {neighbor['name']} ({neighbor['type']}) - {neighbor['relation']} - {neighbor['direction']}")
    
    lines.append("=" * 60)
    
    report = "\n".join(lines)
    
    if output_path:
        output_path = os.path.expanduser(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph Visualization")
    parser.add_argument("--db", default=None, help="Database path")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--format", "-f", choices=["html", "png", "text", "summary"], 
                        default="text", help="Output format")
    parser.add_argument("--entity", "-e", type=str, help="Entity name for detailed report")
    parser.add_argument("--max-entities", "-m", type=int, default=100, 
                        help="Max entities for graph")
    
    args = parser.parse_args()
    
    if args.format == "html":
        if not HAS_PYVIS:
            print("Error: pyvis not installed. Run: pip3 install pyvis --break-system-packages")
            sys.exit(1)
        output = generate_html_graph(args.db, args.output or "graph.html", args.max_entities)
        print(f"Graph saved to: {output}")
    
    elif args.format == "summary":
        summary = generate_text_summary(args.db)
        if args.output:
            with open(os.path.expanduser(args.output), 'w', encoding='utf-8') as f:
                f.write(summary)
        else:
            print(summary)
    
    elif args.format == "text" and args.entity:
        report = generate_entity_report(args.db, args.entity, args.output)
        print(report)
    
    else:
        # Default: show summary
        summary = generate_text_summary(args.db)
        print(summary)


if __name__ == "__main__":
    main()
