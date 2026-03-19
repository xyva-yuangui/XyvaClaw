#!/usr/bin/env python3
"""
Excel/XLSX Tool — 读取、创建、分析 Excel 文件。

Commands: read, create, analyze, convert
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "excel"


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def cmd_read(filepath: str, sheet: str = None, rows: int = 0) -> dict:
    """Read an Excel file and output as JSON."""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed. Run: pip install pandas openpyxl"}

    if not os.path.isfile(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        kwargs = {"engine": "openpyxl"}
        if sheet:
            kwargs["sheet_name"] = sheet

        df = pd.read_excel(filepath, **kwargs)
        if rows > 0:
            df = df.head(rows)

        result = {
            "file": filepath,
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "preview": json.loads(df.head(10).to_json(orient="records", force_ascii=False)),
        }

        if sheet:
            result["sheet"] = sheet

        print(f"✅ 读取成功: {filepath} ({df.shape[0]}行 x {df.shape[1]}列)")
        return result

    except Exception as e:
        return {"error": str(e)}


def cmd_create(data: list, output: str = None, sheet: str = "Sheet1") -> dict:
    """Create an Excel file from JSON data."""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed. Run: pip install pandas openpyxl"}

    _ensure_dir()
    if not output:
        output = str(OUTPUT_DIR / f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    try:
        df = pd.DataFrame(data)
        df.to_excel(output, sheet_name=sheet, index=False, engine="openpyxl")
        print(f"✅ 创建成功: {output} ({df.shape[0]}行 x {df.shape[1]}列)")
        return {"file": output, "shape": list(df.shape), "timestamp": _now()}
    except Exception as e:
        return {"error": str(e)}


def cmd_analyze(filepath: str) -> dict:
    """Analyze an Excel file — basic statistics."""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed"}

    if not os.path.isfile(filepath):
        return {"error": f"File not found: {filepath}"}

    try:
        df = pd.read_excel(filepath, engine="openpyxl")
        stats = {
            "file": filepath,
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns),
            "null_counts": {col: int(df[col].isnull().sum()) for col in df.columns},
            "numeric_stats": {},
        }

        numeric_cols = df.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            stats["numeric_stats"][col] = {
                "mean": round(float(df[col].mean()), 2),
                "min": round(float(df[col].min()), 2),
                "max": round(float(df[col].max()), 2),
                "std": round(float(df[col].std()), 2),
            }

        print(f"✅ 分析完成: {filepath}")
        print(f"   {stats['rows']}行 x {stats['columns']}列, {len(numeric_cols)}个数值列")
        return stats

    except Exception as e:
        return {"error": str(e)}


def cmd_convert(filepath: str, to_format: str = "csv") -> dict:
    """Convert Excel to CSV or JSON."""
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed"}

    if not os.path.isfile(filepath):
        return {"error": f"File not found: {filepath}"}

    _ensure_dir()
    base = Path(filepath).stem

    try:
        df = pd.read_excel(filepath, engine="openpyxl")
        if to_format == "csv":
            out = str(OUTPUT_DIR / f"{base}.csv")
            df.to_csv(out, index=False)
        elif to_format == "json":
            out = str(OUTPUT_DIR / f"{base}.json")
            df.to_json(out, orient="records", force_ascii=False, indent=2)
        else:
            return {"error": f"Unsupported format: {to_format}"}

        print(f"✅ 转换完成: {out}")
        return {"output": out, "format": to_format, "rows": int(df.shape[0])}

    except Exception as e:
        return {"error": str(e)}


def health_check() -> dict:
    checks = [{"name": "python3", "status": "ok"}]
    for mod, pkg in [("openpyxl", "openpyxl"), ("pandas", "pandas")]:
        try:
            __import__(mod)
            checks.append({"name": pkg, "status": "ok"})
        except ImportError:
            checks.append({"name": pkg, "status": "warn", "message": f"pip install {pkg}"})
    overall = "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {"skill": "excel-xlsx", "version": "1.0.0", "status": overall,
            "checks": checks, "timestamp": _now()}


def main():
    parser = argparse.ArgumentParser(description="Excel/XLSX Tool")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")

    sub = parser.add_subparsers(dest="command")

    p_read = sub.add_parser("read")
    p_read.add_argument("file")
    p_read.add_argument("--sheet")
    p_read.add_argument("--rows", type=int, default=0)

    p_create = sub.add_parser("create")
    p_create.add_argument("--data", required=True, help="JSON array string")
    p_create.add_argument("--output")
    p_create.add_argument("--sheet", default="Sheet1")

    p_analyze = sub.add_parser("analyze")
    p_analyze.add_argument("file")

    p_convert = sub.add_parser("convert")
    p_convert.add_argument("file")
    p_convert.add_argument("--format", default="csv", choices=["csv", "json"])

    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    result = None
    if args.command == "read":
        result = cmd_read(args.file, args.sheet, args.rows)
    elif args.command == "create":
        data = json.loads(args.data)
        result = cmd_create(data, args.output, args.sheet)
    elif args.command == "analyze":
        result = cmd_analyze(args.file)
    elif args.command == "convert":
        result = cmd_convert(args.file, args.format)

    if args.json and result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
