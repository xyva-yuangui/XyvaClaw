#!/usr/bin/env python3
"""Dependency check for pdf-processor skill."""
import sys

def check():
    ok = True
    try:
        import pdfplumber
        print(f"✅ pdfplumber {pdfplumber.__version__}")
    except ImportError:
        print("❌ pdfplumber not installed. Run: pip3 install pdfplumber")
        ok = False
    try:
        import PyPDF2
        print(f"✅ PyPDF2 {PyPDF2.__version__}")
    except ImportError:
        print("❌ PyPDF2 not installed. Run: pip3 install PyPDF2")
        ok = False
    return ok

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
