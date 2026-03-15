#!/usr/bin/env python3
"""Dependency check for voice skill."""
import sys, shutil

def check():
    ok = True
    # TTS
    try:
        import edge_tts
        print("✅ edge-tts (TTS engine)")
    except ImportError:
        print("❌ edge-tts not installed. Run: pip3 install edge-tts")
        ok = False

    # STT - optional
    try:
        import openai
        print(f"✅ openai (STT via Whisper API)")
    except ImportError:
        print("⚠️ openai not installed (optional for STT). Run: pip3 install openai")

    # ffmpeg for audio conversion
    if shutil.which("ffmpeg"):
        print("✅ ffmpeg")
    else:
        print("⚠️ ffmpeg not found (needed for some audio formats)")

    return ok

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
