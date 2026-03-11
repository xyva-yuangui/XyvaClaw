#!/usr/bin/env python3
"""
TTS 文案转 Opus 音频文件
用于飞书机器人语音消息发送

使用方法:
    python3 tts_to_opus.py --text "你好，这是一段语音消息" --output /path/to/output.opus
    python3 tts_to_opus.py --text "Hello!" --voice en-US-GuyNeural --output hello.opus

输出的 .opus 文件可以直接通过飞书 API 发送为语音消息
"""
import argparse
import asyncio
import subprocess
import sys
import os
import tempfile
from pathlib import Path

FFMPEG = '/opt/homebrew/bin/ffmpeg'
FFPROBE = '/opt/homebrew/bin/ffprobe'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'output' / 'audio'


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def tts_to_mp3(text: str, voice: str, mp3_path: str):
    """Edge TTS 生成 MP3"""
    try:
        import edge_tts
    except ImportError:
        print("❌ 缺少 edge-tts: pip3 install edge-tts")
        sys.exit(1)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(mp3_path)


def mp3_to_opus(mp3_path: str, opus_path: str) -> bool:
    """MP3 转 Opus（飞书要求的格式）"""
    cmd = (
        f'{FFMPEG} -y -i "{mp3_path}" '
        f'-c:a libopus -b:a 32k -ar 16000 -ac 1 '
        f'"{opus_path}"'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0


def get_duration_ms(path: str) -> int:
    """获取音频时长（毫秒）"""
    try:
        result = subprocess.run(
            [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True
        )
        return int(float(result.stdout.strip()) * 1000)
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description='TTS 文案转 Opus 语音')
    parser.add_argument('--text', '-t', required=True, help='文案内容')
    parser.add_argument('--voice', '-v', default='zh-CN-YunxiNeural',
                        help='语音（默认: zh-CN-YunxiNeural）')
    parser.add_argument('--output', '-o', help='输出 opus 文件路径')
    args = parser.parse_args()

    if not args.output:
        ensure_output_dir()
        from datetime import datetime
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = str(OUTPUT_DIR / f'voice_{ts}.opus')

    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path = os.path.join(tmpdir, 'tts.mp3')

        print(f"🔊 生成 TTS...")
        asyncio.run(tts_to_mp3(args.text, args.voice, mp3_path))

        print(f"🔄 转换为 Opus...")
        if not mp3_to_opus(mp3_path, args.output):
            print("❌ Opus 转换失败")
            sys.exit(1)

    duration_ms = get_duration_ms(args.output)
    print(f"✅ 语音生成完成: {args.output}")
    print(f"   时长: {duration_ms}ms")
    print(f"   duration_ms={duration_ms}")


if __name__ == '__main__':
    main()
