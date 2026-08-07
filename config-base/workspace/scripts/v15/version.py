#!/usr/bin/env python3
"""
V15 版本注册表 — 提供版本信息和组件状态查询
用法:
  python3 scripts/v15/version.py          # 打印版本信息
  python3 scripts/v15/version.py --check  # 检查所有组件状态
"""

import json
import os
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", os.path.expanduser("~/.openclaw/workspace")))
VERSION_FILE = WORKSPACE / "config" / "VERSION.json"
SCRIPTS_DIR = WORKSPACE / "scripts"

VERSION = "15.0.0"
CODENAME = "god-maker"


def load_version_info() -> dict:
    if VERSION_FILE.exists():
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": VERSION, "codename": CODENAME, "components": {}}


def check_components() -> list[dict]:
    info = load_version_info()
    results = []
    for name, comp in info.get("components", {}).items():
        fpath = SCRIPTS_DIR / comp["file"]
        exists = fpath.exists()
        results.append({
            "name": name,
            "file": comp["file"],
            "status": comp.get("status", "unknown"),
            "exists": exists,
            "replaces": comp.get("replaces"),
        })
    return results


def update_component_status(component_name: str, status: str):
    info = load_version_info()
    if component_name in info.get("components", {}):
        info["components"][component_name]["status"] = status
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    info = load_version_info()

    if "--check" in sys.argv:
        print(f"OpenClaw V{info['version']} ({info['codename']})")
        print("=" * 60)
        results = check_components()
        for r in results:
            icon = "✅" if r["exists"] else "⏳" if r["status"] == "pending" else "❌"
            print(f"  {icon} {r['name']:25s} [{r['status']:8s}] {r['file']}")
        ready = sum(1 for r in results if r["exists"])
        total = len(results)
        print(f"\n进度: {ready}/{total} 组件就绪")
    else:
        print(f"OpenClaw V{info['version']} — {info['codename']}")
        print(f"组件数: {len(info.get('components', {}))}")
        print(f"废弃数: {len(info.get('deprecated', []))}")
