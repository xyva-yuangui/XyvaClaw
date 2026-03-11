#!/usr/bin/env python3
"""git skill health check — verifies git and related tools."""
import json, sys, shutil, subprocess
from datetime import datetime

def health_check():
    checks = []
    for tool in ["git", "gh"]:
        checks.append({"name": tool, "status": "ok" if shutil.which(tool) else ("fail" if tool == "git" else "warn")})
    # Check git version
    try:
        r = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
        checks.append({"name": "git_version", "status": "ok", "message": r.stdout.strip()})
    except Exception:
        pass
    checks.append({"name": "python3", "status": "ok"})
    overall = "fail" if any(c["status"]=="fail" for c in checks) else \
              "warn" if any(c["status"]=="warn" for c in checks) else "ok"
    return {"skill": "git", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": datetime.now().isoformat(timespec="seconds")}

if __name__ == "__main__":
    if "--check" in sys.argv:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)
    print("Usage: python check.py --check")
