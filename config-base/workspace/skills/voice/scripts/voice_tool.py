#!/usr/bin/env python3
"""Voice Tool — TTS (edge-tts) + STT (Whisper API / local).

Usage:
  python3 voice_tool.py tts --text "你好" --output hello.mp3
  python3 voice_tool.py tts --text "Hello" --voice en-US-AriaNeural --output hello.mp3
  python3 voice_tool.py tts-voices --lang zh
  python3 voice_tool.py stt --input audio.mp3
  python3 voice_tool.py stt --input audio.mp3 --engine local
"""
from __future__ import annotations
import argparse, asyncio, json, os, sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = os.path.join(
    os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.xyvaclaw")),
    "workspace", "output", "audio"
)

# Default voices per language
DEFAULT_VOICES = {
    "zh": "zh-CN-XiaoxiaoNeural",
    "en": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
}


async def tts(text: str, output_path: str, voice: str | None = None, rate: str = "+0%"):
    """Convert text to speech using edge-tts."""
    try:
        import edge_tts
    except ImportError:
        sys.exit("edge-tts not installed. Run: pip3 install edge-tts")

    if not voice:
        # Auto-detect language
        has_cjk = any('\u4e00' <= c <= '\u9fff' for c in text)
        voice = DEFAULT_VOICES.get("zh" if has_cjk else "en", "en-US-AriaNeural")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    file_size = os.path.getsize(output_path)
    print(f"✅ TTS: {output_path} ({file_size // 1024}KB, voice: {voice})")
    return output_path


async def list_voices(lang: str | None = None):
    """List available TTS voices."""
    try:
        import edge_tts
    except ImportError:
        sys.exit("edge-tts not installed. Run: pip3 install edge-tts")

    voices = await edge_tts.list_voices()
    if lang:
        voices = [v for v in voices if v["Locale"].lower().startswith(lang.lower())]

    for v in voices:
        gender = v.get("Gender", "Unknown")
        print(f"  {v['ShortName']:30s}  {v['Locale']:10s}  {gender}")
    print(f"\nTotal: {len(voices)} voices")
    return voices


def stt_api(input_path: str, lang: str | None = None) -> str:
    """Transcribe audio using OpenAI Whisper API."""
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("openai not installed. Run: pip3 install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Try DeepSeek or other compatible API
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    else:
        base_url = "https://api.openai.com/v1"

    if not api_key:
        sys.exit("Set OPENAI_API_KEY environment variable for Whisper STT")

    client = OpenAI(api_key=api_key, base_url=base_url)

    with open(input_path, "rb") as f:
        kwargs = {"model": "whisper-1", "file": f}
        if lang:
            kwargs["language"] = lang
        transcript = client.audio.transcriptions.create(**kwargs)

    text = transcript.text
    print(f"✅ STT: {text}")
    return text


def stt_local(input_path: str, lang: str | None = None) -> str:
    """Transcribe audio using local whisper.cpp."""
    import subprocess, shutil

    whisper_bin = shutil.which("whisper-cpp") or shutil.which("whisper")
    if not whisper_bin:
        sys.exit("whisper-cpp not found. Install: brew install whisper-cpp")

    cmd = [whisper_bin, "-f", input_path, "--output-txt"]
    if lang:
        cmd.extend(["-l", lang])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        sys.exit(f"whisper-cpp failed: {result.stderr}")

    text = result.stdout.strip()
    print(f"✅ STT (local): {text}")
    return text


def main():
    parser = argparse.ArgumentParser(description="Voice Tool (TTS + STT)")
    sub = parser.add_subparsers(dest="cmd")

    # tts
    t = sub.add_parser("tts", help="Text to Speech")
    t.add_argument("--text", "-t", required=True)
    t.add_argument("--output", "-o", default=None)
    t.add_argument("--voice", "-v", default=None, help="e.g. zh-CN-XiaoxiaoNeural")
    t.add_argument("--rate", default="+0%", help="Speed: -50% to +50%")

    # tts-voices
    tv = sub.add_parser("tts-voices", help="List available TTS voices")
    tv.add_argument("--lang", "-l", default=None, help="Filter by language code (zh, en, ja)")

    # stt
    s = sub.add_parser("stt", help="Speech to Text")
    s.add_argument("--input", "-i", required=True)
    s.add_argument("--lang", "-l", default=None, help="Language hint (zh, en)")
    s.add_argument("--engine", "-e", default="api", choices=["api", "local"])

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    if args.cmd == "tts":
        output = args.output or os.path.join(DEFAULT_OUTPUT_DIR, "tts_output.mp3")
        asyncio.run(tts(args.text, output, args.voice, args.rate))

    elif args.cmd == "tts-voices":
        asyncio.run(list_voices(args.lang))

    elif args.cmd == "stt":
        if args.engine == "local":
            stt_local(args.input, args.lang)
        else:
            stt_api(args.input, args.lang)


if __name__ == "__main__":
    main()
