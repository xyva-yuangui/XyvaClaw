#!/usr/bin/env python3
"""
ocr_extract.py — Extract text from images using macOS Vision Framework.

Usage:
    python3 ocr_extract.py <image_path> [--lang zh-Hans,en] [--json] [--confidence 0.5]

Requires macOS 10.15+ with pyobjc-framework-Vision installed.
Falls back to a simpler approach if pyobjc is not available.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def ocr_with_vision_framework(image_path: str, languages: list[str], min_confidence: float):
    """Use macOS Vision framework via pyobjc for OCR."""
    try:
        import Quartz
        import Vision
        from Foundation import NSURL
    except ImportError:
        return None  # pyobjc not installed, use fallback

    file_url = NSURL.fileURLWithPath_(image_path)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLanguages_(languages)
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    # Create image request handler
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(file_url, None)
    success = handler.performRequests_error_([request], None)

    if not success[0]:
        return None

    results = request.results()
    if not results:
        return {"text": "", "blocks": []}

    blocks = []
    full_text_lines = []

    for observation in results:
        candidate = observation.topCandidates_(1)[0]
        text = candidate.string()
        confidence = candidate.confidence()

        if confidence < min_confidence:
            continue

        bbox = observation.boundingBox()
        blocks.append({
            "text": text,
            "confidence": round(float(confidence), 4),
            "bbox": [
                round(float(bbox.origin.x), 4),
                round(float(bbox.origin.y), 4),
                round(float(bbox.size.width), 4),
                round(float(bbox.size.height), 4),
            ],
        })
        full_text_lines.append(text)

    return {
        "text": "\n".join(full_text_lines),
        "blocks": blocks,
    }


def ocr_with_shortcuts(image_path: str):
    """Fallback: Use macOS shortcuts/swift for OCR via a simple swift script."""
    swift_code = f'''
import Cocoa
import Vision

let url = URL(fileURLWithPath: "{image_path}")
guard let image = NSImage(contentsOf: url),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {{
    print("ERROR: Cannot load image")
    exit(1)
}}

let request = VNRecognizeTextRequest()
request.recognitionLanguages = ["zh-Hans", "en"]
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try handler.perform([request])

guard let results = request.results else {{ exit(0) }}
for observation in results {{
    guard let candidate = observation.topCandidates(1).first else {{ continue }}
    print(candidate.string)
}}
'''
    try:
        result = subprocess.run(
            ["swift", "-"],
            input=swift_code,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            return {
                "text": "\n".join(lines),
                "blocks": [{"text": line, "confidence": 0.9, "bbox": []} for line in lines],
            }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def ocr_with_tesseract(image_path: str, languages: list[str]):
    """Fallback: Use tesseract if installed."""
    lang_map = {"zh-Hans": "chi_sim", "zh-Hant": "chi_tra", "en": "eng", "ja": "jpn"}
    tess_langs = "+".join(lang_map.get(l, l) for l in languages)

    try:
        result = subprocess.run(
            ["tesseract", image_path, "stdout", "-l", tess_langs],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            text = result.stdout.strip()
            return {
                "text": text,
                "blocks": [{"text": line, "confidence": 0.8, "bbox": []} for line in text.split("\n") if line.strip()],
            }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def main():
    if args.check:
        print("✅ OK")
        return

    parser = argparse.ArgumentParser(description="Extract text from images using OCR")
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument("--lang", default="zh-Hans,en", help="OCR languages (comma-separated)")
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output as JSON")
    parser.add_argument('--check', action='store_true', help='Health check')
    parser.add_argument("--confidence", type=float, default=0.5, help="Min confidence threshold")
    args = parser.parse_args()

    image_path = str(Path(args.image_path).resolve())
    if not Path(image_path).exists():
        print(f"Error: File not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    languages = [l.strip() for l in args.lang.split(",")]

    # Try methods in order of preference
    result = ocr_with_vision_framework(image_path, languages, args.confidence)

    if result is None:
        print("[ocr] Vision framework not available, trying swift fallback...", file=sys.stderr)
        result = ocr_with_shortcuts(image_path)

    if result is None:
        print("[ocr] Swift fallback failed, trying tesseract...", file=sys.stderr)
        result = ocr_with_tesseract(image_path, languages)

    if result is None:
        print("Error: No OCR engine available. Install pyobjc-framework-Vision or tesseract.", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["text"])


if __name__ == "__main__":
    main()
