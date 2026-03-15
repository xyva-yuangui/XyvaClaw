#!/usr/bin/env python3
"""PDF Processor — extract text, tables, merge, split, info.

Usage:
  python3 pdf_tool.py extract-text --input doc.pdf [--pages 1-5]
  python3 pdf_tool.py extract-tables --input doc.pdf [--format csv|json]
  python3 pdf_tool.py merge --inputs a.pdf b.pdf --output merged.pdf
  python3 pdf_tool.py split --input doc.pdf --pages 1-3 --output part.pdf
  python3 pdf_tool.py info --input doc.pdf
  python3 pdf_tool.py to-images --input doc.pdf --output-dir ./images/
"""
from __future__ import annotations
import argparse, csv, io, json, os, sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = os.path.join(
    os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.xyvaclaw")),
    "workspace", "output", "pdf"
)


def _parse_pages(pages_str: str, max_page: int) -> list[int]:
    """Parse '1-5' or '1,3,5' into list of 0-indexed page numbers."""
    result = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start, end = int(start), int(end)
            result.extend(range(max(0, start - 1), min(end, max_page)))
        else:
            idx = int(part) - 1
            if 0 <= idx < max_page:
                result.append(idx)
    return sorted(set(result))


def extract_text(input_path: str, pages: str | None = None):
    """Extract text from PDF."""
    import pdfplumber
    with pdfplumber.open(input_path) as pdf:
        total = len(pdf.pages)
        page_indices = _parse_pages(pages, total) if pages else range(total)
        texts = []
        for i in page_indices:
            page = pdf.pages[i]
            text = page.extract_text() or ""
            texts.append(f"--- Page {i + 1} ---\n{text}")
        result = "\n\n".join(texts)
        print(result)
        return result


def extract_tables(input_path: str, fmt: str = "csv"):
    """Extract tables from PDF."""
    import pdfplumber
    all_tables = []
    with pdfplumber.open(input_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for t_idx, table in enumerate(tables):
                all_tables.append({
                    "page": i + 1,
                    "table_index": t_idx,
                    "data": table
                })

    if fmt == "json":
        print(json.dumps(all_tables, ensure_ascii=False, indent=2))
    else:
        for t in all_tables:
            print(f"\n--- Page {t['page']}, Table {t['table_index']} ---")
            writer = csv.writer(sys.stdout)
            for row in t["data"]:
                writer.writerow(row or [])

    return all_tables


def merge_pdfs(input_paths: list[str], output_path: str):
    """Merge multiple PDFs into one."""
    from PyPDF2 import PdfMerger
    merger = PdfMerger()
    for path in input_paths:
        if not os.path.exists(path):
            print(f"⚠️ File not found: {path}", file=sys.stderr)
            continue
        merger.append(path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    merger.write(output_path)
    merger.close()
    print(f"✅ Merged {len(input_paths)} PDFs → {output_path}")


def split_pdf(input_path: str, pages: str, output_path: str):
    """Split PDF by page range."""
    from PyPDF2 import PdfReader, PdfWriter
    reader = PdfReader(input_path)
    writer = PdfWriter()
    page_indices = _parse_pages(pages, len(reader.pages))

    for i in page_indices:
        writer.add_page(reader.pages[i])

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"✅ Split pages {pages} → {output_path} ({len(page_indices)} pages)")


def pdf_info(input_path: str):
    """Show PDF metadata."""
    from PyPDF2 import PdfReader
    reader = PdfReader(input_path)
    meta = reader.metadata
    info = {
        "file": input_path,
        "pages": len(reader.pages),
        "title": meta.title if meta else None,
        "author": meta.author if meta else None,
        "creator": meta.creator if meta else None,
        "producer": meta.producer if meta else None,
    }
    for k, v in info.items():
        print(f"  {k}: {v}")
    return info


def to_images(input_path: str, output_dir: str):
    """Convert PDF pages to PNG images."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        sys.exit("pdf2image not installed. Run: pip3 install pdf2image\nAlso requires poppler: brew install poppler")
    os.makedirs(output_dir, exist_ok=True)
    images = convert_from_path(input_path)
    paths = []
    for i, img in enumerate(images):
        path = os.path.join(output_dir, f"page_{i + 1:03d}.png")
        img.save(path, "PNG")
        paths.append(path)
    print(f"✅ Converted {len(images)} pages → {output_dir}")
    return paths


def main():
    parser = argparse.ArgumentParser(description="PDF Processor")
    sub = parser.add_subparsers(dest="cmd")

    # extract-text
    et = sub.add_parser("extract-text")
    et.add_argument("--input", "-i", required=True)
    et.add_argument("--pages", "-p", default=None, help="e.g. 1-5 or 1,3,5")

    # extract-tables
    tb = sub.add_parser("extract-tables")
    tb.add_argument("--input", "-i", required=True)
    tb.add_argument("--format", "-f", default="csv", choices=["csv", "json"])

    # merge
    mg = sub.add_parser("merge")
    mg.add_argument("--inputs", nargs="+", required=True)
    mg.add_argument("--output", "-o", default=os.path.join(DEFAULT_OUTPUT_DIR, "merged.pdf"))

    # split
    sp = sub.add_parser("split")
    sp.add_argument("--input", "-i", required=True)
    sp.add_argument("--pages", "-p", required=True)
    sp.add_argument("--output", "-o", default=os.path.join(DEFAULT_OUTPUT_DIR, "split.pdf"))

    # info
    inf = sub.add_parser("info")
    inf.add_argument("--input", "-i", required=True)

    # to-images
    ti = sub.add_parser("to-images")
    ti.add_argument("--input", "-i", required=True)
    ti.add_argument("--output-dir", "-o", default=os.path.join(DEFAULT_OUTPUT_DIR, "images"))

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    if args.cmd == "extract-text":
        extract_text(args.input, args.pages)
    elif args.cmd == "extract-tables":
        extract_tables(args.input, args.format)
    elif args.cmd == "merge":
        merge_pdfs(args.inputs, args.output)
    elif args.cmd == "split":
        split_pdf(args.input, args.pages, args.output)
    elif args.cmd == "info":
        pdf_info(args.input)
    elif args.cmd == "to-images":
        to_images(args.input, args.output_dir)


if __name__ == "__main__":
    main()
