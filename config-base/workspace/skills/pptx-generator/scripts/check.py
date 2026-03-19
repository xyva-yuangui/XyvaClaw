#!/usr/bin/env python3
"""Dependency check for pptx-generator skill."""
import subprocess, sys

def check():
    ok = True
    try:
        import pptx
        print(f"✅ python-pptx {pptx.__version__}")
    except ImportError:
        print("❌ python-pptx not installed. Run: pip3 install python-pptx")
        ok = False
    return ok

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
