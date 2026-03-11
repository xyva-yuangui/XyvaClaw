#!/usr/bin/env python3
"""
TTS 语音引擎 - 基于 Edge TTS（微软免费服务）
"""
import argparse
import asyncio
import sys


async def generate_tts(text: str, voice: str, output: str):
    try:
        import edge_tts
    except ImportError:
        print("❌ 缺少 edge-tts，请安装: pip3 install edge-tts")
        sys.exit(1)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)
    print(f"✅ TTS 生成完成: {output}")


async def get_audio_duration(path: str) -> float:
    """获取音频时长（秒）"""
    import subprocess
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description='TTS 语音生成')
    parser.add_argument('--text', '-t', required=True, help='文案')
    parser.add_argument('--voice', '-v', default='zh-CN-YunxiNeural',
                        help='语音选择')
    parser.add_argument('--output', '-o', required=True, help='输出路径')
    parser.add_argument('--duration', action='store_true',
                        help='生成后输出音频时长')
    args = parser.parse_args()

    asyncio.run(generate_tts(args.text, args.voice, args.output))

    if args.duration:
        dur = asyncio.run(get_audio_duration(args.output))
        print(f"时长: {dur:.2f}s")


if __name__ == '__main__':
    main()
