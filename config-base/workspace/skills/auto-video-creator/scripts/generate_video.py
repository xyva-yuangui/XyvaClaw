#!/usr/bin/env python3
"""
OpenClaw 自动视频生成 - 主入口脚本
支持：图文轮播、文字动画、卡片风格、AI视频大模型

依赖：
    pip3 install edge-tts
    ffmpeg (已安装)
    playwright (已安装，卡片模式用)
"""
import argparse
import os
import sys
import subprocess
import tempfile
import shutil
import json
import time
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'output' / 'video'
FFMPEG = '/opt/homebrew/bin/ffmpeg'
FFPROBE = '/opt/homebrew/bin/ffprobe'


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def default_output_path(prefix='video'):
    ensure_output_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return str(OUTPUT_DIR / f'{prefix}_{ts}.mp4')


def run_cmd(cmd, desc=''):
    """运行命令并打印状态"""
    if desc:
        print(f"  ⏳ {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ 命令失败: {cmd[:100]}")
        if result.stderr:
            print(f"     错误: {result.stderr[:300]}")
        return False
    return True


def get_audio_duration(path):
    """获取音频/视频时长（秒）"""
    try:
        result = subprocess.run(
            [FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def generate_tts(text, voice, output_path):
    """生成 TTS 语音"""
    tts_script = SCRIPT_DIR / 'tts_engine.py'
    escaped_text = text.replace('"', '\\"')
    cmd = f'python3 "{tts_script}" --text "{escaped_text}" --voice "{voice}" --output "{output_path}"'
    return run_cmd(cmd, 'TTS 语音生成')


# ============================================================
# 类型 1: 图文轮播视频 (slideshow)
# ============================================================
def cmd_slideshow(args):
    """图文轮播：多张图片 + 音频/TTS"""
    print("\n🎬 生成图文轮播视频")

    images = args.images
    output = args.output or default_output_path('slideshow')
    width = args.width
    height = args.height
    fps = args.fps
    transition = args.transition

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = None

        # 生成或使用音频
        if args.audio:
            audio_path = args.audio
        elif args.text:
            audio_path = os.path.join(tmpdir, 'tts.mp3')
            if not generate_tts(args.text, args.voice, audio_path):
                print("❌ TTS 生成失败")
                sys.exit(1)

        # 计算每张图片时长
        if audio_path:
            total_dur = get_audio_duration(audio_path)
            per_image = max(total_dur / len(images), 2.0)
        else:
            per_image = args.duration or 3.0
            total_dur = per_image * len(images)

        print(f"  📊 总时长: {total_dur:.1f}s, 每张: {per_image:.1f}s, 图片数: {len(images)}")

        # 构建 ffmpeg 滤镜
        inputs = []
        filter_parts = []

        for i, img in enumerate(images):
            inputs.extend(['-loop', '1', '-t', str(per_image), '-i', img])
            # 缩放每张图片到目标尺寸
            filter_parts.append(
                f'[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,'
                f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,'
                f'setsar=1[img{i}]'
            )

        # 拼接
        concat_inputs = ''.join(f'[img{i}]' for i in range(len(images)))

        if transition == 'fade' and len(images) > 1:
            # 使用 xfade 做淡入淡出
            fade_dur = min(0.5, per_image * 0.2)
            current = '[img0]'
            for i in range(1, len(images)):
                offset = per_image * i - fade_dur * i
                out_label = f'[xf{i}]' if i < len(images) - 1 else '[vout]'
                filter_parts.append(
                    f'{current}[img{i}]xfade=transition=fade:duration={fade_dur}:offset={offset:.2f}{out_label}'
                )
                current = f'[xf{i}]'
        else:
            filter_parts.append(f'{concat_inputs}concat=n={len(images)}:v=1:a=0[vout]')

        filter_complex = ';'.join(filter_parts)

        # 构建完整命令
        cmd_parts = [FFMPEG, '-y']
        cmd_parts.extend(inputs)

        if audio_path:
            cmd_parts.extend(['-i', audio_path])

        cmd_parts.extend(['-filter_complex', filter_complex, '-map', '[vout]'])

        if audio_path:
            audio_idx = len(images)
            cmd_parts.extend(['-map', f'{audio_idx}:a', '-shortest'])

        if args.bgm:
            # 混合背景音乐
            cmd_parts.extend([
                '-i', args.bgm,
                '-filter_complex',
                f'[{len(images) + (1 if audio_path else 0)}:a]volume={args.bgm_volume}[bgm];'
                f'{"[" + str(len(images)) + ":a]" if audio_path else "anullsrc=r=44100:cl=stereo[silence];[silence]"}'
                f'[bgm]amix=inputs=2:duration=shortest[aout]',
                '-map', '[aout]'
            ])

        cmd_parts.extend([
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            output
        ])

        cmd_str = ' '.join(f'"{p}"' if ' ' in str(p) else str(p) for p in cmd_parts)
        if run_cmd(cmd_str, '视频编码'):
            print(f"\n✅ 图文轮播视频生成完成: {output}")
        else:
            print("\n❌ 视频生成失败")
            sys.exit(1)


# ============================================================
# 类型 2: 文字动画视频 (text-anim)
# ============================================================
def cmd_text_anim(args):
    """文字动画：文案逐段显示 + TTS"""
    print("\n🎬 生成文字动画视频")

    text = args.text
    output = args.output or default_output_path('text_anim')
    width = args.width
    height = args.height
    bg_color = args.bg_color
    voice = args.voice

    with tempfile.TemporaryDirectory() as tmpdir:
        # 分段
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if not paragraphs:
            print("❌ 没有有效的文案内容")
            sys.exit(1)

        print(f"  📝 文案段落: {len(paragraphs)} 段")

        # 为每段生成 TTS
        segment_files = []
        for i, para in enumerate(paragraphs):
            tts_path = os.path.join(tmpdir, f'tts_{i}.mp3')
            if not generate_tts(para, voice, tts_path):
                print(f"  ⚠️ 第 {i+1} 段 TTS 失败，跳过")
                continue

            dur = get_audio_duration(tts_path)
            # 生成纯色背景 + 文字叠加的视频片段
            seg_path = os.path.join(tmpdir, f'seg_{i}.mp4')

            # 用 ffmpeg drawtext 绘制文字
            safe_text = para.replace("'", "\\'").replace('"', '\\"').replace(':', '\\:')
            # 自动换行：每行约 15 个中文字符
            wrapped = wrap_text(para, 15)
            safe_wrapped = wrapped.replace("'", "\\'").replace('"', '\\"').replace(':', '\\:')

            cmd = (
                f'{FFMPEG} -y -f lavfi -i "color=c=0x{bg_color}:s={width}x{height}:d={dur}" '
                f'-i "{tts_path}" '
                f'-vf "drawtext=text=\'{safe_wrapped}\':'
                f'fontsize=52:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:'
                f'line_spacing=20" '
                f'-c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k '
                f'-pix_fmt yuv420p -shortest "{seg_path}"'
            )
            if run_cmd(cmd, f'渲染第 {i+1} 段'):
                segment_files.append(seg_path)

        if not segment_files:
            print("❌ 没有成功生成的视频片段")
            sys.exit(1)

        # 拼接所有片段
        concat_list = os.path.join(tmpdir, 'concat.txt')
        with open(concat_list, 'w') as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        cmd = (
            f'{FFMPEG} -y -f concat -safe 0 -i "{concat_list}" '
            f'-c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k '
            f'-pix_fmt yuv420p "{output}"'
        )

        if run_cmd(cmd, '拼接视频'):
            dur = get_audio_duration(output)
            print(f"\n✅ 文字动画视频生成完成: {output} ({dur:.1f}s)")
        else:
            print("\n❌ 视频拼接失败")
            sys.exit(1)


def wrap_text(text, chars_per_line=15):
    """简单的中文文本换行"""
    lines = []
    current = ''
    for ch in text:
        current += ch
        if len(current) >= chars_per_line:
            lines.append(current)
            current = ''
    if current:
        lines.append(current)
    return '\n'.join(lines)


# ============================================================
# 类型 3: 卡片风格视频 (card)
# ============================================================
def cmd_card(args):
    """卡片风格：小红书风格卡片转视频"""
    print("\n🎬 生成卡片风格视频")

    markdown_path = args.markdown
    output = args.output or default_output_path('card')
    width = args.width
    height = args.height
    voice = args.voice

    if not os.path.exists(markdown_path):
        print(f"❌ Markdown 文件不存在: {markdown_path}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 使用小红书渲染脚本生成卡片图片
        xhs_render = (Path.home() / '.openclaw' / 'workspace' / 'skills' /
                      'auto-redbook-skills-0.1.0' / 'scripts' / 'render_xhs.py')

        if not xhs_render.exists():
            print("❌ 找不到小红书渲染脚本 render_xhs.py")
            print("  请确认 auto-redbook-skills-0.1.0 技能已安装")
            sys.exit(1)

        # 渲染卡片
        img_dir = os.path.join(tmpdir, 'cards')
        os.makedirs(img_dir, exist_ok=True)
        cmd = f'python3 "{xhs_render}" -i "{markdown_path}" -o "{img_dir}"'
        if not run_cmd(cmd, '渲染卡片图片'):
            print("❌ 卡片渲染失败")
            sys.exit(1)

        # 收集生成的图片
        images = sorted([
            os.path.join(img_dir, f) for f in os.listdir(img_dir)
            if f.endswith(('.png', '.jpg', '.jpeg'))
        ])

        if not images:
            print("❌ 没有生成任何卡片图片")
            sys.exit(1)

        print(f"  🖼️ 生成了 {len(images)} 张卡片")

        # 读取 markdown 提取文案用于 TTS
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 去掉 YAML 头部
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                text_content = parts[2].strip()
            else:
                text_content = content
        else:
            text_content = content

        # 生成 TTS
        tts_path = os.path.join(tmpdir, 'narration.mp3')
        if text_content:
            # 清理 markdown 标记
            import re
            clean_text = re.sub(r'[#*`\[\]()>]', '', text_content)
            clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
            clean_text = re.sub(r'\n{2,}', '\n', clean_text).strip()

            if generate_tts(clean_text, voice, tts_path):
                print("  🔊 TTS 旁白已生成")
            else:
                tts_path = None
        else:
            tts_path = None

        # 委托给 slideshow 逻辑
        class FakeArgs:
            pass
        fake = FakeArgs()
        fake.images = images
        fake.output = output
        fake.width = width
        fake.height = height
        fake.fps = args.fps
        fake.voice = voice
        fake.transition = args.transition
        fake.bgm = args.bgm
        fake.bgm_volume = args.bgm_volume
        fake.audio = tts_path
        fake.text = None
        fake.duration = None

        cmd_slideshow(fake)


# ============================================================
# 类型 4: AI视频大模型 (ai-video)
# ============================================================
def cmd_ai_video(args):
    """AI视频大模型：通过百炼API生成视频"""
    print("\n🎬 AI视频大模型生成")

    prompt = args.prompt
    output = args.output or default_output_path('ai_video')
    duration = args.ai_duration or 5

    print(f"  📝 提示词: {prompt}")
    print(f"  ⏱️ 目标时长: {duration}s")

    # 使用百炼 API 调用视频生成模型
    # 百炼支持的视频生成模型：通过 dashscope API
    try:
        import requests
    except ImportError:
        print("❌ 缺少 requests 库: pip3 install requests")
        sys.exit(1)

    api_key = None
    # 从 openclaw.json 读取百炼 API key
    config_path = Path.home() / '.openclaw' / 'openclaw.json'
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        providers = config.get('models', {}).get('providers', {})
        if 'bailian' in providers:
            api_key = providers['bailian'].get('apiKey')

    if not api_key:
        print("❌ 未找到百炼 API Key")
        print("  请确认 ~/.openclaw/openclaw.json 中配置了 bailian provider")
        sys.exit(1)

    # 调用 dashscope 视频生成 API（异步任务）
    print("  📡 提交视频生成任务到百炼...")
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-DashScope-Async': 'enable',
    }

    # 使用通义万相-视频生成模型
    payload = {
        'model': 'wanx-v1',
        'input': {
            'prompt': prompt,
        },
        'parameters': {
            'duration': duration,
            'size': '1080*1920',  # 竖屏
        }
    }

    try:
        resp = requests.post(
            'https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/generation',
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code == 200:
            result = resp.json()
            task_id = result.get('output', {}).get('task_id')
            if task_id:
                print(f"  ✅ 任务已提交，task_id: {task_id}")
                print("  ⏳ 等待视频生成（通常需要 1-5 分钟）...")

                # 轮询任务状态
                poll_url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
                poll_headers = {'Authorization': f'Bearer {api_key}'}

                for attempt in range(60):  # 最多等 5 分钟
                    time.sleep(5)
                    poll_resp = requests.get(poll_url, headers=poll_headers, timeout=10)
                    if poll_resp.status_code == 200:
                        status_data = poll_resp.json()
                        status = status_data.get('output', {}).get('task_status')
                        print(f"    状态: {status}")

                        if status == 'SUCCEEDED':
                            video_url = status_data.get('output', {}).get('video_url')
                            if not video_url:
                                results = status_data.get('output', {}).get('results', [])
                                if results:
                                    video_url = results[0].get('url')

                            if video_url:
                                print(f"  📥 下载视频...")
                                video_resp = requests.get(video_url, timeout=120)
                                with open(output, 'wb') as f:
                                    f.write(video_resp.content)
                                print(f"\n✅ AI视频生成完成: {output}")
                                return
                            else:
                                print("  ❌ 任务成功但未返回视频URL")
                                print(f"     完整响应: {json.dumps(status_data, indent=2, ensure_ascii=False)[:500]}")
                                sys.exit(1)

                        elif status == 'FAILED':
                            error_msg = status_data.get('output', {}).get('message', '未知错误')
                            print(f"  ❌ 视频生成失败: {error_msg}")
                            sys.exit(1)

                print("  ❌ 等待超时，请稍后通过 task_id 查询结果")
                sys.exit(1)
            else:
                print(f"  ❌ 未获取到 task_id: {json.dumps(result, indent=2, ensure_ascii=False)[:300]}")
                sys.exit(1)
        else:
            error_body = resp.text[:300]
            print(f"  ❌ API 调用失败 (HTTP {resp.status_code}): {error_body}")
            print("\n💡 可能原因:")
            print("  1. 百炼 API Key 没有视频生成权限")
            print("  2. 视频生成模型未开通")
            print("  3. 请在百炼控制台开通通义万相-视频生成")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"  ❌ 网络请求失败: {e}")
        sys.exit(1)


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='OpenClaw 自动视频生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 图文轮播
  python3 generate_video.py slideshow -i img1.png img2.png -t "旁白文案"

  # 文字动画
  python3 generate_video.py text-anim -t "第一段\\n第二段\\n第三段"

  # 卡片风格
  python3 generate_video.py card -m content.md

  # AI视频大模型
  python3 generate_video.py ai-video --prompt "一只猫在花园里追蝴蝶"
'''
    )

    subparsers = parser.add_subparsers(dest='command')

    # 共用参数
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--output', '-o', help='输出文件路径')
    common.add_argument('--width', '-w', type=int, default=1080)
    common.add_argument('--height', type=int, default=1920)
    common.add_argument('--fps', type=int, default=30)
    common.add_argument('--voice', default='zh-CN-YunxiNeural')
    common.add_argument('--bgm', help='背景音乐路径')
    common.add_argument('--bgm-volume', type=float, default=0.3)
    common.add_argument('--transition', choices=['fade', 'slide', 'none'],
                        default='fade')

    # slideshow
    p_slide = subparsers.add_parser('slideshow', parents=[common],
                                     help='图文轮播视频')
    p_slide.add_argument('--images', '-i', nargs='+', required=True)
    p_slide.add_argument('--audio', '-a', help='音频文件')
    p_slide.add_argument('--text', '-t', help='文案（自动生成 TTS）')
    p_slide.add_argument('--duration', type=float, help='每张图片时长')

    # text-anim
    p_text = subparsers.add_parser('text-anim', parents=[common],
                                    help='文字动画视频')
    p_text.add_argument('--text', '-t', required=True)
    p_text.add_argument('--bg-color', default='0A0A1A')

    # card
    p_card = subparsers.add_parser('card', parents=[common],
                                    help='卡片风格视频')
    p_card.add_argument('--markdown', '-m', required=True)
    p_card.add_argument('--theme', default='default')

    # ai-video
    p_ai = subparsers.add_parser('ai-video', parents=[common],
                                  help='AI视频大模型生成')
    p_ai.add_argument('--prompt', '-p', required=True, help='视频描述提示词')
    p_ai.add_argument('--ai-duration', type=int, default=5,
                       help='视频时长（秒，默认5）')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'slideshow':
        cmd_slideshow(args)
    elif args.command == 'text-anim':
        cmd_text_anim(args)
    elif args.command == 'card':
        cmd_card(args)
    elif args.command == 'ai-video':
        cmd_ai_video(args)


if __name__ == '__main__':
    main()
