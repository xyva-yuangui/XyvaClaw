#!/usr/bin/env python3
"""
Knowledge Graph - Daily Decay Cron Job

Run this daily to decay entity scores and prune low-score entities.

Usage:
    python3 kg_decay_cron.py [--prune-threshold 0.05] [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add kg.py to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from kg import get_db, run_decay, prune, stats


def main():
    parser = argparse.ArgumentParser(description="KG Daily Decay Cron Job")
    parser.add_argument("--prune-threshold", type=float, default=0.05,
                        help="Decay score threshold for pruning (default: 0.05)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    db_path = os.path.expanduser("~/.openclaw/memory/knowledge-graph.sqlite")
    conn = get_db(db_path)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "db_path": db_path,
        "dry_run": args.dry_run,
        "before": {},
        "after": {},
        "actions": []
    }
    
    try:
        # Get stats before
        s_before = stats(conn)
        result["before"] = {
            "entities": s_before["entities"],
            "relations": s_before["relations"],
            "avg_decay": s_before["avg_decay_score"]
        }
        
        # Run decay
        if not args.dry_run:
            run_decay(conn)
            result["actions"].append("decay executed")
        else:
            result["actions"].append("decay skipped (dry run)")
        
        # Run prune
        pruned = conn.execute(
            "SELECT id, name, decay_score FROM entities WHERE decay_score < ?",
            (args.prune_threshold,)
        ).fetchall()
        
        if pruned:
            if not args.dry_run:
                prune(conn, args.prune_threshold)
                result["actions"].append(f"pruned {len(pruned)} entities")
            else:
                result["actions"].append(f"would prune {len(pruned)} entities")
                result["to_prune"] = [{"name": p["name"], "score": p["decay_score"]} for p in pruned]
        else:
            result["actions"].append("no entities to prune")
        
        # Get stats after
        s_after = stats(conn)
        result["after"] = {
            "entities": s_after["entities"],
            "relations": s_after["relations"],
            "avg_decay": s_after["avg_decay_score"]
        }
        
        # Summary
        result["summary"] = {
            "entities_change": s_after["entities"] - s_before["entities"],
            "relations_change": s_after["relations"] - s_before["relations"],
            "decay_improvement": s_after["avg_decay_score"] - s_before["avg_decay_score"]
        }
        
    except Exception as e:
        result["error"] = str(e)
    finally:
        conn.close()
    
    # Output
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("Knowledge Graph - Daily Decay Job")
        print("=" * 60)
        print(f"Timestamp: {result['timestamp']}")
        print(f"Dry Run: {result['dry_run']}")
        print()
        print("Before:")
        print(f"  Entities: {result['before']['entities']}")
        print(f"  Relations: {result['before']['relations']}")
        print(f"  Avg Decay: {result['before']['avg_decay']}")
        print()
        print("Actions:")
        for action in result['actions']:
            print(f"  - {action}")
        if result.get('to_prune'):
            print("  Entities to prune:")
            for ent in result['to_prune']:
                print(f"    - {ent['name']} (score: {ent['score']})")
        print()
        print("After:")
        print(f"  Entities: {result['after']['entities']}")
        print(f"  Relations: {result['after']['relations']}")
        print(f"  Avg Decay: {result['after']['avg_decay']}")
        print()
        print("Summary:")
        print(f"  Entities Change: {result['summary']['entities_change']}")
        print(f"  Relations Change: {result['summary']['relations_change']}")
        print(f"  Decay Improvement: {result['summary']['decay_improvement']:.4f}")
        print("=" * 60)


if __name__ == "__main__":
    main()
