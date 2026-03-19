#!/usr/bin/env python3
"""
OpenClaw Semantic Cache
========================
Caches LLM responses keyed by query embedding similarity.
If a new query is semantically similar (cosine > threshold) to a cached query,
returns the cached response instantly — saving LLM API cost and latency.

Usage:
    # Check cache before calling LLM
    python3 semantic_cache.py check "用户问题"

    # Store response after LLM call
    python3 semantic_cache.py store "用户问题" "LLM响应内容"

    # Stats
    python3 semantic_cache.py stats

    # Clear cache
    python3 semantic_cache.py clear
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

OPENCLAW_HOME = Path.home() / ".openclaw"
CHROMA_DIR = OPENCLAW_HOME / "data" / "chromadb"
CACHE_COLLECTION = "_semantic_cache"
SIMILARITY_THRESHOLD = 0.92  # cosine similarity threshold for cache hit
CACHE_TTL_HOURS = 24         # cache entries expire after this
EMBEDDING_MODEL = "text-embedding-v3"
EMBEDDING_DIM = 1024
MAX_CACHE_SIZE = 500         # max cached entries


def resolve_api_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if key:
        return key
    try:
        cfg_path = OPENCLAW_HOME / "openclaw.json"
        with open(cfg_path) as f:
            cfg = json.load(f)
        key = cfg.get("models", {}).get("providers", {}).get("bailian", {}).get("apiKey", "")
        if key and not key.startswith("sk-sp-"):
            return key
    except Exception:
        pass
    print("ERROR: No DASHSCOPE_API_KEY", file=sys.stderr)
    sys.exit(1)


def get_embedding(text: str, api_key: str) -> list[float]:
    import urllib.request
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    payload = {"model": EMBEDDING_MODEL, "input": [text], "dimensions": EMBEDDING_DIM}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    return result["data"][0]["embedding"]


def get_chroma_client():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def cmd_check(args):
    api_key = resolve_api_key()
    query = args.query.strip()
    if not query:
        print(json.dumps({"hit": False, "reason": "empty query"}))
        return

    client = get_chroma_client()
    try:
        col = client.get_collection(CACHE_COLLECTION)
    except Exception:
        print(json.dumps({"hit": False, "reason": "no cache collection"}))
        return

    if col.count() == 0:
        print(json.dumps({"hit": False, "reason": "cache empty"}))
        return

    emb = get_embedding(query, api_key)
    results = col.query(query_embeddings=[emb], n_results=1, include=["documents", "metadatas", "distances"])

    if not results["documents"] or not results["documents"][0]:
        print(json.dumps({"hit": False, "reason": "no results"}))
        return

    dist = results["distances"][0][0]
    score = 1 - dist
    meta = results["metadatas"][0][0]
    cached_response = results["documents"][0][0]

    # Check TTL
    stored_at = meta.get("stored_at", 0)
    age_hours = (time.time() - stored_at) / 3600
    if age_hours > CACHE_TTL_HOURS:
        print(json.dumps({"hit": False, "reason": f"expired (age={age_hours:.1f}h)", "score": round(score, 3)}))
        return

    if score >= SIMILARITY_THRESHOLD:
        print(json.dumps({
            "hit": True,
            "score": round(score, 3),
            "cached_query": meta.get("query", ""),
            "response": cached_response,
            "age_hours": round(age_hours, 1),
        }, ensure_ascii=False))
    else:
        print(json.dumps({"hit": False, "reason": f"score too low ({score:.3f})", "score": round(score, 3)}))


def cmd_store(args):
    api_key = resolve_api_key()
    query = args.query.strip()
    response = args.response.strip()
    if not query or not response:
        print("ERROR: query and response required", file=sys.stderr)
        return

    client = get_chroma_client()
    col = client.get_or_create_collection(CACHE_COLLECTION, metadata={"hnsw:space": "cosine"})

    # Evict oldest if at capacity
    if col.count() >= MAX_CACHE_SIZE:
        all_data = col.get(include=["metadatas"])
        if all_data["ids"]:
            entries = list(zip(all_data["ids"], all_data["metadatas"]))
            entries.sort(key=lambda e: e[1].get("stored_at", 0))
            to_remove = [e[0] for e in entries[:50]]  # remove oldest 50
            col.delete(ids=to_remove)

    import hashlib
    doc_id = hashlib.md5(query.encode()).hexdigest()[:16]
    emb = get_embedding(query, api_key)

    # Upsert
    col.upsert(
        ids=[doc_id],
        embeddings=[emb],
        documents=[response],
        metadatas=[{"query": query[:200], "stored_at": time.time(), "response_len": len(response)}],
    )
    print(f"Cached: {query[:60]}... ({len(response)} chars)")


def cmd_stats(args):
    client = get_chroma_client()
    try:
        col = client.get_collection(CACHE_COLLECTION)
        count = col.count()
        print(f"Semantic cache: {count} entries (max {MAX_CACHE_SIZE})")
        print(f"TTL: {CACHE_TTL_HOURS}h, threshold: {SIMILARITY_THRESHOLD}")
    except Exception:
        print("Semantic cache: not initialized")


def cmd_clear(args):
    client = get_chroma_client()
    try:
        client.delete_collection(CACHE_COLLECTION)
        print("Cache cleared.")
    except Exception:
        print("No cache to clear.")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Semantic Cache")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Check cache for similar query")
    p_check.add_argument("query")

    p_store = sub.add_parser("store", help="Store query-response pair")
    p_store.add_argument("query")
    p_store.add_argument("response")

    sub.add_parser("stats", help="Show cache stats")
    sub.add_parser("clear", help="Clear cache")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"check": cmd_check, "store": cmd_store, "stats": cmd_stats, "clear": cmd_clear}[args.command](args)


if __name__ == "__main__":
    main()
