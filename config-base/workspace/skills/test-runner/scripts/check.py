#!/usr/bin/env python3
"""test-runner health check — verifies testing tools available."""
import json, sys, shutil
from datetime import datetime

def health_check():
    checks = []
    for tool, name in [("pytest", "pytest"), ("jest", "jest"), ("node", "node")]:
        checks.append({"name": name, "status": "ok" if shutil.which(tool) else "warn"})
    checks.append({"name": "python3", "status": "ok"})
    overall = "fail" if any(c["status"]=="fail" for c in checks) else \
              "warn" if any(c["status"]=="warn" for c in checks) else "ok"
    return {"skill": "test-runner", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": datetime.now().isoformat(timespec="seconds")}

if __name__ == "__main__":
    if "--check" in sys.argv:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)
    print("Usage: python check.py --check")
