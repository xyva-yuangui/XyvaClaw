#!/usr/bin/env python3
"""excel-xlsx health check — verifies openpyxl/pandas available."""
import json, sys
from datetime import datetime

def health_check():
    checks = [{"name": "python3", "status": "ok"}]
    for mod in ["openpyxl", "pandas", "xlsxwriter"]:
        try:
            __import__(mod)
            checks.append({"name": mod, "status": "ok"})
        except ImportError:
            checks.append({"name": mod, "status": "warn", "message": f"pip install {mod}"})
    overall = "warn" if any(c["status"]=="warn" for c in checks) else "ok"
    return {"skill": "excel-xlsx", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": datetime.now().isoformat(timespec="seconds")}

if __name__ == "__main__":
    if "--check" in sys.argv:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)
    print("Usage: python check.py --check")
