#!/usr/bin/env python3

import argparse
import json
import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]
TARGET_SCRIPT = SKILLS_ROOT / "python-dataviz" / "scripts" / "interactive.py"


def health_check() -> dict:
    checks = [
        {
            "name": "interactive.py",
            "status": "ok" if TARGET_SCRIPT.is_file() else "fail",
            "message": str(TARGET_SCRIPT),
        }
    ]
    for module_name in ["plotly", "pandas", "numpy"]:
        try:
            __import__(module_name)
            checks.append({"name": module_name, "status": "ok", "message": "installed"})
        except ImportError:
            checks.append({"name": module_name, "status": "warn", "message": f"missing: {module_name}"})
    overall = "fail" if any(item["status"] == "fail" for item in checks) else "warn" if any(item["status"] == "warn" for item in checks) else "ok"
    return {
        "skill": "python-dataviz-interactive",
        "status": overall,
        "checks": checks,
    }


def run_examples() -> int:
    if not TARGET_SCRIPT.is_file():
        print(f"❌ target script missing: {TARGET_SCRIPT}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(TARGET_SCRIPT)])
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive dataviz adapter")
    parser.add_argument("command", nargs="?", choices=["run", "check"], default="run")
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    if args.command == "check":
        result = health_check()
        if args.as_json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for item in result["checks"]:
                icon = "✅" if item["status"] == "ok" else ("⚠️" if item["status"] == "warn" else "❌")
                print(f"{icon} {item['name']}: {item['message']}")
        return 0 if result["status"] != "fail" else 1

    return run_examples()


if __name__ == "__main__":
    raise SystemExit(main())
