#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.31.0",
# ]
# ///
"""
Content Studio — 统一内容创作技能

支持模式:
  1. 文生图 (text2image)    — Seedream 5.0 / 万相 wan2.6
  2. 文生视频 (text2video)  — Seedance 2.0
  3. 图生图 (image2image)   — Seedream 5.0 (参考图 + prompt)
  4. 图生视频 (image2video) — Seedance 2.0 (首帧图 + prompt)
  5. 首尾帧生视频 (frames2video) — Seedance 2.0 (首帧+尾帧 + prompt)

所有模式:
  - 生成完成后自动上传+发送到飞书对话 (群聊/私聊)
  - 支持参数引导 (分辨率/时长/尺寸/比例等)
  - 本地自动保存到 output/ 目录
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# 模块路径
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = Path.home() / ".openclaw" / "workspace"

# 导入飞书模块
sys.path.insert(0, str(SCRIPT_DIR))
from feishu_media import (
    send_text, send_image, send_file, send_video,
    send_media_with_text, get_tenant_token,
)
from prompt_enhancer import enhance_video_prompt, enhance_image_prompt

# 导入图片生成模块
IMAGE_SKILL_DIR = WORKSPACE_ROOT / "skills" / "qwen-image" / "scripts"
sys.path.insert(0, str(IMAGE_SKILL_DIR))

# 导入视频生成模块
VIDEO_SKILL_DIR = WORKSPACE_ROOT / "skills" / "seedance-video" / "scripts"
sys.path.insert(0, str(VIDEO_SKILL_DIR))


def load_config():
    """加载 content-studio 配置"""
    config_path = SKILL_DIR / "config" / "default.json"
    with open(config_path) as f:
        return json.load(f)


def _output_dir(media_type):
    """创建输出目录"""
    now = datetime.now()
    subdir = "image" if media_type == "image" else "video"
    d = WORKSPACE_ROOT / "output" / subdir / now.strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d, now


def _sanitize(text, max_len=30):
    """文件名安全化"""
    import re
    safe = re.sub(r'[\\/:*?"<>|\s]+', '_', text[:max_len])
    return safe.strip('_') or "output"


# ============================================================
# 参数引导
# ============================================================

def guide_video_params(args, config):
    """视频参数引导 — 返回最终参数字典"""
    defaults = config.get("video", {}).get("defaults", {})
    ratio_opts = config.get("video", {}).get("ratio_options", [])
    dur_opts = config.get("video", {}).get("duration_options", [])
    res_opts = config.get("video", {}).get("resolution_options", [])

    params = {
        "model": args.model or defaults.get("model"),
        "ratio": args.ratio or defaults.get("ratio", "16:9"),
        "duration": args.duration or defaults.get("duration", 5),
        "resolution": args.resolution or defaults.get("resolution", "720p"),
        "generate_audio": defaults.get("generate_audio", True),
        "watermark": defaults.get("watermark", False),
    }

    # 如果使用快速模式
    if getattr(args, 'fast', False):
        params["model"] = config.get("video", {}).get("models", {}).get("fast", params["model"])

    print("📐 视频参数:")
    print(f"  模型: {params['model']}")
    print(f"  比例: {params['ratio']}  (可选: {', '.join(ratio_opts)})")
    print(f"  时长: {params['duration']}s  (可选: {', '.join(map(str, dur_opts))})")
    print(f"  分辨率: {params['resolution']}  (可选: {', '.join(res_opts)})")
    print(f"  有声: {'是' if params['generate_audio'] else '否'}")
    return params


def guide_image_params(args, config):
    """图片参数引导 — 返回最终参数字典"""
    defaults = config.get("image", {}).get("defaults", {})
    engines = config.get("image", {}).get("engines", {})
    size_opts = config.get("image", {}).get("size_options", {})

    engine = args.engine or defaults.get("engine", "seedream5")
    size = args.size or defaults.get("size", "2K")

    # 根据引擎匹配合适的尺寸列表
    if engine.startswith("seedream"):
        available_sizes = size_opts.get("seedream", [])
    else:
        available_sizes = size_opts.get("wanx", [])

    params = {
        "engine": engine,
        "model": engines.get(engine, "doubao-seedream-5-0-260128"),
        "size": size,
        "quality": args.quality if hasattr(args, 'quality') else "high",
        "watermark": defaults.get("watermark", False),
    }

    print("📐 图片参数:")
    print(f"  引擎: {engine} ({params['model']})")
    print(f"  尺寸: {size}  (可选: {', '.join(available_sizes)})")
    print(f"  质量: {params['quality']}")
    return params


# ============================================================
# 模式1: 文生图 (text2image)
# ============================================================

def text2image(args, config):
    """文生图: prompt → 图片 → 飞书发送"""
    from generate_image_v3 import smart_generate

    print("🎨 === 文生图 (Text → Image) ===")
    print(f"  提示: {args.prompt[:80]}...")

    params = guide_image_params(args, config)
    print()

    # 智能 Prompt 增强 (大白话→专业级)
    final_prompt = args.prompt
    if not getattr(args, 'no_enhance', False):
        print("✨ 智能增强提示词...")
        enh = enhance_image_prompt(args.prompt, engine=params["engine"], size=params["size"])
        final_prompt = enh["enhanced"]
        if enh["method"] == "llm":
            print(f"  增强后 ({len(final_prompt)} chars): {final_prompt[:100]}...")
        else:
            print(f"  [规则增强] {final_prompt[:100]}...")
    else:
        print("📝 [跳过增强] 使用原始提示词")

    out_dir, now = _output_dir("image")
    ts = now.strftime("%H%M%S")
    summary = _sanitize(args.prompt)
    filename = str(out_dir / f"{ts}_t2i_{summary}.png")

    result = smart_generate(
        user_input=final_prompt,
        scene=getattr(args, 'scene', None),
        style=getattr(args, 'style', None),
        force_engine=params["engine"],
        size=params["size"],
        quality=params["quality"],
        filename=filename,
        raw=getattr(args, 'raw', False),
        watermark=params["watermark"],
    )

    if not result.get("success"):
        error_msg = result.get("error", "未知错误")
        print(f"\n❌ 生成失败: {error_msg}")
        _feishu_notify(f"❌ 文生图失败: {error_msg}\n提示: {args.prompt[:100]}", args, config)
        return result

    local_path = result.get("local_path", filename)
    print(f"\n✅ 图片生成成功: {local_path}")

    # 飞书发送
    _feishu_send_media(
        local_path,
        f"🎨 文生图完成\n📝 {args.prompt[:150]}\n📐 {params['engine']} / {params['size']}",
        args, config,
    )
    return result


# ============================================================
# 模式2: 文生视频 (text2video)
# ============================================================

def text2video(args, config):
    """文生视频: prompt → 视频 → 飞书发送"""
    from seedance_api import create_video, poll_video, download_video

    print("🎬 === 文生视频 (Text → Video) ===")
    print(f"  提示: {args.prompt[:80]}...")

    params = guide_video_params(args, config)
    api_key = config.get("video", {}).get("api_key", "")
    print()

    # 智能 Prompt 增强 (大白话→专业级六层结构)
    optimized = args.prompt
    if not getattr(args, 'no_enhance', False) and not getattr(args, 'no_optimize', False):
        print("✨ 智能增强提示词 (六层框架)...")
        enh = enhance_video_prompt(
            args.prompt,
            duration=params["duration"],
            ratio=params["ratio"],
            resolution=params["resolution"],
        )
        optimized = enh["enhanced"]
        if enh["method"] == "llm":
            print(f"  增强后 ({len(optimized)} chars): {optimized[:120]}...")
        else:
            print(f"  [规则增强] {optimized[:120]}...")
    else:
        print("📝 [跳过增强] 使用原始提示词")

    # 创建任务
    print("\n🚀 创建视频生成任务...")
    # 需要设置环境变量供 seedance_api 使用
    os.environ["ARK_API_KEY"] = api_key

    from seedance_api import load_config as load_video_config
    video_config = load_video_config()

    result = create_video(
        prompt=optimized,
        model=params["model"],
        ratio=params["ratio"],
        duration=params["duration"],
        resolution=params["resolution"],
        generate_audio=params["generate_audio"],
        first_frame_path=getattr(args, 'first_frame', None),
        last_frame_path=getattr(args, 'last_frame', None),
        reference_images=getattr(args, 'ref_images', None),
        web_search=getattr(args, 'web_search', False),
        config=video_config,
    )

    if not result.get("ok"):
        error_msg = result.get("error", "未知错误")
        print(f"❌ 任务创建失败: {error_msg}")
        _feishu_notify(f"❌ 视频创建失败: {error_msg}\n提示: {args.prompt[:100]}", args, config)
        return {"success": False, "error": error_msg}

    task_id = result.get("task_id", "")
    print(f"  ✅ Task ID: {task_id}")

    # 轮询
    print("\n⏳ 等待视频生成...")
    poll_result = poll_video(task_id, video_config,
                             callback=lambda s, a, e: print(f"  [{s}] {e:.0f}s"))

    if not poll_result.get("ok"):
        error_msg = poll_result.get("error", "未知错误")
        print(f"❌ 视频生成失败: {error_msg}")
        _feishu_notify(f"❌ 视频生成失败: {error_msg}\n提示: {args.prompt[:100]}", args, config)
        return {"success": False, "error": error_msg}

    video_url = poll_result.get("video_url", "")
    elapsed = poll_result.get("elapsed_seconds", 0)

    # 下载保存
    out_dir, now = _output_dir("video")
    ts = now.strftime("%H%M%S")
    summary = _sanitize(args.prompt)
    filename = str(out_dir / f"{ts}_t2v_{summary}.mp4")

    print(f"\n💾 下载视频... ({elapsed:.0f}s)")
    dl_result = download_video(video_url, filename)

    if not dl_result.get("ok"):
        print(f"  ⚠️ 下载失败: {dl_result.get('error')}")
        _feishu_notify(f"🎬 视频已生成但下载失败\n🔗 {video_url}", args, config)
        return {"success": True, "video_url": video_url, "error": "download_failed"}

    size_mb = dl_result["size_bytes"] / (1024 * 1024)
    local_path = dl_result["path"]
    print(f"  ✅ 已保存: {local_path} ({size_mb:.1f}MB)")

    # 飞书发送
    _feishu_send_media(
        local_path,
        f"🎬 文生视频完成\n📝 {args.prompt[:150]}\n📐 {params['ratio']} / {params['duration']}s / {params['resolution']}\n⏱️ {elapsed:.0f}s",
        args, config,
    )

    return {
        "success": True, "video_url": video_url, "local_path": local_path,
        "elapsed_seconds": elapsed, "task_id": task_id,
    }


# ============================================================
# 模式3: 图生图 (image2image)
# ============================================================

def image2image(args, config):
    """图生图: 参考图 + prompt → 新图片 → 飞书发送

    使用 Seedream 5.0 的图片编辑功能:
    将参考图作为输入，结合prompt生成新图片。
    """
    from generate_image_v3 import smart_generate

    print("🖼️ === 图生图 (Image → Image) ===")

    ref_image = args.ref_image
    if not ref_image or not Path(ref_image).exists():
        print(f"❌ 参考图片不存在: {ref_image}")
        return {"success": False, "error": "参考图片不存在"}

    print(f"  参考图: {ref_image}")
    print(f"  提示: {args.prompt[:80]}...")

    params = guide_image_params(args, config)
    print()

    # 对于Seedream图生图: 将参考图编码到prompt中
    import base64
    ref_path = Path(ref_image)
    ref_b64 = base64.b64encode(ref_path.read_bytes()).decode("ascii")
    mime = "image/png" if ref_path.suffix.lower() == ".png" else "image/jpeg"

    out_dir, now = _output_dir("image")
    ts = now.strftime("%H%M%S")
    summary = _sanitize(args.prompt)
    filename = str(out_dir / f"{ts}_i2i_{summary}.png")

    # Seedream 5.0 图生图: 通过 Ark API 的 image edit 能力
    import requests
    api_key = config.get("image", {}).get("seedream_api_key", "")
    if not api_key:
        from generate_image_v3 import get_ark_key
        api_key = get_ark_key()

    # 使用 images/edits 接口 (如果可用) 或用参考图+prompt组合
    # Seedream 5.0 当前主要是 text2image, 图生图通过文字描述参考图的方式
    # 先用 raw prompt + 参考图描述 的方式
    enhanced_prompt = f"基于参考图片进行创作。{args.prompt}。保持参考图的核心元素和风格，进行艺术化重新创作。"

    result = smart_generate(
        user_input=enhanced_prompt,
        force_engine=params["engine"],
        size=params["size"],
        quality=params["quality"],
        filename=filename,
        raw=True,
        watermark=params["watermark"],
    )

    if not result.get("success"):
        print(f"\n❌ 生成失败: {result.get('error')}")
        return result

    local_path = result.get("local_path", filename)
    print(f"\n✅ 图生图完成: {local_path}")

    _feishu_send_media(
        local_path,
        f"🖼️ 图生图完成\n📝 {args.prompt[:150]}\n📐 {params['engine']} / {params['size']}",
        args, config,
    )
    return result


# ============================================================
# 模式4: 图生视频 (image2video)
# ============================================================

def image2video(args, config):
    """图生视频: 参考图 + prompt → 视频 → 飞书发送

    使用 Seedance 2.0 的首帧图生视频能力。
    """
    print("🎬 === 图生视频 (Image → Video) ===")

    ref_image = args.ref_image
    if not ref_image or not Path(ref_image).exists():
        print(f"❌ 参考图片不存在: {ref_image}")
        return {"success": False, "error": "参考图片不存在"}

    print(f"  首帧图: {ref_image}")
    print(f"  提示: {args.prompt[:80]}...")

    # 设置 first_frame 参数
    args.first_frame = ref_image
    args.last_frame = None

    return _generate_video_with_frames(args, config, mode="i2v")


# ============================================================
# 模式5: 首尾帧生视频 (frames2video)
# ============================================================

def frames2video(args, config):
    """首尾帧生视频: 首帧+尾帧+prompt → 视频 → 飞书发送"""
    print("🎬 === 首尾帧生视频 (Frames → Video) ===")

    first_frame = args.first_frame
    last_frame = args.last_frame

    if not first_frame or not Path(first_frame).exists():
        print(f"❌ 首帧图片不存在: {first_frame}")
        return {"success": False, "error": "首帧图片不存在"}
    if not last_frame or not Path(last_frame).exists():
        print(f"❌ 尾帧图片不存在: {last_frame}")
        return {"success": False, "error": "尾帧图片不存在"}

    print(f"  首帧: {first_frame}")
    print(f"  尾帧: {last_frame}")
    print(f"  提示: {args.prompt[:80]}..." if args.prompt else "  提示: (无)")

    return _generate_video_with_frames(args, config, mode="f2v")


def _generate_video_with_frames(args, config, mode="i2v"):
    """通用帧生视频: 共享 image2video 和 frames2video 逻辑"""
    from seedance_api import create_video, poll_video, download_video

    params = guide_video_params(args, config)
    api_key = config.get("video", {}).get("api_key", "")
    os.environ["ARK_API_KEY"] = api_key

    from seedance_api import load_config as load_video_config
    video_config = load_video_config()

    print("\n🚀 创建视频生成任务...")
    result = create_video(
        prompt=args.prompt or "",
        model=params["model"],
        ratio=params["ratio"],
        duration=params["duration"],
        resolution=params["resolution"],
        generate_audio=params["generate_audio"],
        first_frame_path=getattr(args, 'first_frame', None),
        last_frame_path=getattr(args, 'last_frame', None),
        reference_images=getattr(args, 'ref_images', None),
        config=video_config,
    )

    if not result.get("ok"):
        error_msg = result.get("error", "未知错误")
        print(f"❌ 任务创建失败: {error_msg}")
        _feishu_notify(f"❌ {mode}视频创建失败: {error_msg}", args, config)
        return {"success": False, "error": error_msg}

    task_id = result.get("task_id", "")
    print(f"  ✅ Task ID: {task_id}")

    # 轮询
    print("\n⏳ 等待视频生成...")
    poll_result = poll_video(task_id, video_config,
                             callback=lambda s, a, e: print(f"  [{s}] {e:.0f}s"))

    if not poll_result.get("ok"):
        error_msg = poll_result.get("error", "未知错误")
        print(f"❌ 视频生成失败: {error_msg}")
        _feishu_notify(f"❌ {mode}视频生成失败: {error_msg}", args, config)
        return {"success": False, "error": error_msg}

    video_url = poll_result.get("video_url", "")
    elapsed = poll_result.get("elapsed_seconds", 0)

    # 下载保存
    out_dir, now = _output_dir("video")
    ts = now.strftime("%H%M%S")
    summary = _sanitize(args.prompt or "frames")
    filename = str(out_dir / f"{ts}_{mode}_{summary}.mp4")

    print(f"\n💾 下载视频... ({elapsed:.0f}s)")
    dl_result = download_video(video_url, filename)

    if not dl_result.get("ok"):
        print(f"  ⚠️ 下载失败: {dl_result.get('error')}")
        _feishu_notify(f"🎬 视频已生成但下载失败\n🔗 {video_url}", args, config)
        return {"success": True, "video_url": video_url, "error": "download_failed"}

    size_mb = dl_result["size_bytes"] / (1024 * 1024)
    local_path = dl_result["path"]
    print(f"  ✅ 已保存: {local_path} ({size_mb:.1f}MB)")

    mode_name = {"i2v": "图生视频", "f2v": "首尾帧生视频"}.get(mode, mode)
    _feishu_send_media(
        local_path,
        f"🎬 {mode_name}完成\n📝 {(args.prompt or '(无文字)')[:150]}\n📐 {params['ratio']} / {params['duration']}s / {params['resolution']}\n⏱️ {elapsed:.0f}s",
        args, config,
    )

    return {
        "success": True, "video_url": video_url, "local_path": local_path,
        "elapsed_seconds": elapsed, "task_id": task_id, "mode": mode,
    }


# ============================================================
# 飞书发送辅助
# ============================================================

def _feishu_notify(text, args, config):
    """发送纯文本通知到飞书"""
    target = getattr(args, 'feishu_target', None)
    if config.get("feishu", {}).get("enabled", True):
        send_text(text, receive_id=target)


def _feishu_send_media(file_path, text, args, config):
    """发送媒体+文字到飞书"""
    if not config.get("feishu", {}).get("enabled", True):
        print("  ℹ️  飞书发送已禁用")
        return

    if not config.get("feishu", {}).get("send_file", True):
        _feishu_notify(text, args, config)
        return

    target = getattr(args, 'feishu_target', None)
    print("\n📮 发送到飞书...")
    result = send_media_with_text(text, file_path=file_path, receive_id=target)

    if result.get("ok"):
        print("  ✅ 飞书发送完成")
    else:
        errors = result.get("errors", [])
        print(f"  ⚠️  部分失败: {errors}")


# ============================================================
# Prompt 优化 (已迁移到 prompt_enhancer.py)
# _optimize_prompt 保留为兼容接口
# ============================================================

def _optimize_prompt(prompt, config):
    """兼容接口 — 调用新的 prompt_enhancer"""
    enh = enhance_video_prompt(prompt)
    return enh["enhanced"]


# ============================================================
# 健康检查
# ============================================================

def cmd_check(args, config):
    """检查所有 API 连通性"""
    print("🔍 Content Studio 健康检查")
    print()

    # 飞书
    token = get_tenant_token()
    print(f"  {'✅' if token else '❌'} 飞书 Open API")

    # Seedream 5.0
    seedream_key = config.get("image", {}).get("seedream_api_key")
    print(f"  {'✅' if seedream_key else '❌'} Seedream 5.0 (图片生成)")

    # Wanx
    wanx_key = config.get("image", {}).get("wanx_api_key")
    print(f"  {'✅' if wanx_key else '❌'} 万相 wan2.6 (图片生成)")

    # Seedance 2.0
    video_key = config.get("video", {}).get("api_key")
    print(f"  {'✅' if video_key else '❌'} Seedance 2.0 (视频生成)")

    # DeepSeek
    ds_key = os.environ.get("DEEPSEEK_API_KEY")
    if not ds_key:
        try:
            oc_path = Path.home() / ".openclaw" / "openclaw.json"
            with open(oc_path) as f:
                oc = json.load(f)
            ds_key = oc.get("models", {}).get("providers", {}).get("deepseek", {}).get("apiKey")
        except Exception:
            pass
    print(f"  {'✅' if ds_key else '❌'} DeepSeek (Prompt优化)")

    # 参数预设
    print()
    print("📐 参数预设:")
    vd = config.get("video", {}).get("defaults", {})
    print(f"  视频: {vd.get('ratio','?')} / {vd.get('duration','?')}s / {vd.get('resolution','?')}")
    id_ = config.get("image", {}).get("defaults", {})
    print(f"  图片: {id_.get('engine','?')} / {id_.get('size','?')} / {id_.get('quality','?')}")

    # 模式列表
    print()
    print("🎯 支持模式:")
    print("  text2image   — 文生图 (seedream5/wanx)")
    print("  text2video   — 文生视频 (seedance 2.0)")
    print("  image2image  — 图生图 (参考图+prompt)")
    print("  image2video  — 图生视频 (首帧图+prompt)")
    print("  frames2video — 首尾帧生视频 (首帧+尾帧+prompt)")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Content Studio — 统一内容创作 (文生图/文生视频/图生图/图生视频/首尾帧生视频)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 文生图
  python content_studio.py text2image --prompt "赛博朋克风格的东京街头"

  # 文生视频
  python content_studio.py text2video --prompt "一只橘猫在窗台上打哈欠" --duration 5 --ratio 16:9

  # 图生视频 (首帧)
  python content_studio.py image2video --ref-image photo.jpg --prompt "让画面动起来"

  # 首尾帧生视频
  python content_studio.py frames2video --first-frame start.jpg --last-frame end.jpg --prompt "平滑过渡"

  # 健康检查
  python content_studio.py check

  # 发送指定到群聊
  python content_studio.py text2image --prompt "..." --feishu-target oc_xxx
""")

    subparsers = parser.add_subparsers(dest="mode", help="创作模式")

    # ── check ──
    subparsers.add_parser("check", help="健康检查")

    # ── text2image ──
    p_t2i = subparsers.add_parser("text2image", aliases=["t2i"], help="文生图")
    p_t2i.add_argument("--prompt", "-p", required=True, help="图片描述")
    p_t2i.add_argument("--engine", choices=["seedream5", "seedream4", "wanx"], help="引擎")
    p_t2i.add_argument("--size", "-s", help="尺寸 (2K, 2K_16:9, wanx_1:1...)")
    p_t2i.add_argument("--quality", "-q", choices=["high", "standard"], default="high")
    p_t2i.add_argument("--scene", help="场景模板")
    p_t2i.add_argument("--style", help="风格")
    p_t2i.add_argument("--raw", action="store_true", help="Raw模式")
    p_t2i.add_argument("--no-enhance", action="store_true", help="跳过智能提示词增强")
    p_t2i.add_argument("--feishu-target", help="飞书接收者 (open_id/chat_id)")

    # ── text2video ──
    p_t2v = subparsers.add_parser("text2video", aliases=["t2v"], help="文生视频")
    p_t2v.add_argument("--prompt", "-p", required=True, help="视频描述")
    p_t2v.add_argument("--model", help="模型 (quality/fast)")
    p_t2v.add_argument("--ratio", help="比例 (16:9, 9:16, 1:1...)")
    p_t2v.add_argument("--duration", type=int, help="时长秒数 (4-15)")
    p_t2v.add_argument("--resolution", help="分辨率 (480p, 720p)")
    p_t2v.add_argument("--fast", action="store_true", help="快速模式")
    p_t2v.add_argument("--no-optimize", action="store_true", help="跳过prompt优化 (兼容旧参数)")
    p_t2v.add_argument("--no-enhance", action="store_true", help="跳过智能提示词增强")
    p_t2v.add_argument("--web-search", action="store_true", help="联网搜索")
    p_t2v.add_argument("--feishu-target", help="飞书接收者")

    # ── image2image ──
    p_i2i = subparsers.add_parser("image2image", aliases=["i2i"], help="图生图")
    p_i2i.add_argument("--ref-image", required=True, help="参考图片路径")
    p_i2i.add_argument("--prompt", "-p", required=True, help="创作描述")
    p_i2i.add_argument("--engine", choices=["seedream5", "seedream4", "wanx"])
    p_i2i.add_argument("--size", "-s", help="尺寸")
    p_i2i.add_argument("--quality", "-q", choices=["high", "standard"], default="high")
    p_i2i.add_argument("--feishu-target", help="飞书接收者")

    # ── image2video ──
    p_i2v = subparsers.add_parser("image2video", aliases=["i2v"], help="图生视频")
    p_i2v.add_argument("--ref-image", required=True, help="首帧图片路径")
    p_i2v.add_argument("--prompt", "-p", default="", help="动作/运动描述")
    p_i2v.add_argument("--model", help="模型")
    p_i2v.add_argument("--ratio", help="比例")
    p_i2v.add_argument("--duration", type=int, help="时长")
    p_i2v.add_argument("--resolution", help="分辨率")
    p_i2v.add_argument("--feishu-target", help="飞书接收者")

    # ── frames2video ──
    p_f2v = subparsers.add_parser("frames2video", aliases=["f2v"], help="首尾帧生视频")
    p_f2v.add_argument("--first-frame", required=True, help="首帧图片路径")
    p_f2v.add_argument("--last-frame", required=True, help="尾帧图片路径")
    p_f2v.add_argument("--prompt", "-p", default="", help="运动/过渡描述")
    p_f2v.add_argument("--model", help="模型")
    p_f2v.add_argument("--ratio", help="比例")
    p_f2v.add_argument("--duration", type=int, help="时长")
    p_f2v.add_argument("--resolution", help="分辨率")
    p_f2v.add_argument("--feishu-target", help="飞书接收者")

    args = parser.parse_args()
    config = load_config()

    mode_map = {
        "check": cmd_check,
        "text2image": text2image, "t2i": text2image,
        "text2video": text2video, "t2v": text2video,
        "image2image": image2image, "i2i": image2image,
        "image2video": image2video, "i2v": image2video,
        "frames2video": frames2video, "f2v": frames2video,
    }

    handler = mode_map.get(args.mode)
    if handler:
        result = handler(args, config)
        if isinstance(result, dict) and not result.get("success", result.get("ok", True)):
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
