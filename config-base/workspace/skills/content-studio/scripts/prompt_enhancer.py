#!/usr/bin/env python3
"""
Prompt Enhancer — 大白话 → 专业级提示词 (视频 + 图片)

基于 1719 条 Seedance 2.0 顶级 prompt 分析 + 业界最佳实践:

视频六层框架 (67%含镜头语言, 61%含光影, 44%含时间分段):
  L1: 主体与动作 (Subject & Action)
  L2: 镜头与构图 (Shot Type & Framing)
  L3: 运镜与节奏 (Camera Movement & Pacing)
  L4: 光影与氛围 (Lighting & Atmosphere)
  L5: 技术参数 (Technical Specs — Arri/35mm/8K 等)
  L6: 时间线 (Timeline — 仅长视频)

图片五层框架:
  L1: 主体精确描述 (Subject Precision)
  L2: 风格规格 (Style Specification)
  L3: 构图指导 (Compositional Control)
  L4: 光影指令 (Lighting Directives)
  L5: 技术参数 (Technical Parameters)

用法:
  from prompt_enhancer import enhance_video_prompt, enhance_image_prompt

  # 视频: 大白话 → 专业 prompt
  result = enhance_video_prompt("一只猫在桌上打哈欠", duration=5)

  # 图片: 大白话 → 专业 prompt
  result = enhance_image_prompt("赛博朋克风格的东京街头")
"""

import json
import os
import sys
import urllib.request
from pathlib import Path


# ============================================================
# LLM 调用
# ============================================================

def _get_deepseek_key():
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key:
        return key
    try:
        oc = Path.home() / ".openclaw" / "openclaw.json"
        with open(oc) as f:
            return json.load(f).get("models", {}).get("providers", {}).get("deepseek", {}).get("apiKey")
    except Exception:
        return None


def _call_llm(system_prompt, user_prompt, max_tokens=2000):
    """调用 DeepSeek 进行 prompt 增强"""
    api_key = _get_deepseek_key()
    if not api_key:
        print("  ⚠️  无 DeepSeek API Key, 使用规则增强", file=sys.stderr)
        return None

    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode()

    req = urllib.request.Request(
        "https://api.deepseek.com/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  ⚠️  LLM调用失败: {e}", file=sys.stderr)
        return None


# ============================================================
# 视频 Prompt 增强
# ============================================================

VIDEO_SYSTEM_PROMPT = """你是世界顶级的AI视频导演和提示词工程师。你的唯一任务是将用户的简单描述转化为Seedance 2.0能生成高质量视频的专业提示词。

## 你的输出必须包含以下六层结构（自然融合,不要显式标注层级）

### Layer 1: 主体与动作
- 将模糊主体精确化: 外貌特征、服装材质、表情状态
- 将简单动作展开为动态细节: 速度、力度、与环境的交互
- 例: "猫打哈欠" → "毛茸茸的橘色虎斑猫慵懒地蜷在阳光斑驳的木桌上,缓慢张大嘴巴打出一个大大的哈欠,露出粉色舌头,随后满足地眯起眼睛,前爪微微伸展"

### Layer 2: 镜头与构图 (67%的顶级prompt包含)
必须使用的镜头术语(至少选2-3个):
- 景别: extreme close-up/close-up/medium shot/wide shot/extreme wide shot
- 角度: low-angle/high-angle/eye-level/bird's-eye/dutch angle
- 中文: 特写/中景/全景/远景/俯拍/仰拍

### Layer 3: 运镜 (9%用tracking, 5%用handheld)
必须包含至少一种运镜:
- tracking shot/dolly in/dolly out/slow push-in/pull-back
- orbit/pan/tilt/crane shot/steadicam/handheld
- 高级: whip pan/FPV drone/continuous shot/one-take

### Layer 4: 光影与氛围 (61%的顶级prompt包含)
必须描写光影,至少包含2项:
- 光源: golden hour/blue hour/rim lighting/volumetric rays/backlight/Rembrandt lighting
- 氛围: cinematic/dramatic/ethereal/moody/warm/cold
- 效果: lens flare/film grain/bokeh/fog/dust particles/rain
- 中文: 丁达尔效应/轮廓光/逆光/柔和光线

### Layer 5: 技术参数 (Arri 6%, 35mm 3%, 8K 6%)
添加1-2个技术标签:
- 相机: "shot on Arri Alexa"/"anamorphic lens"/"85mm lens"/"35mm film"
- 质感: "high dynamic range"/"4K ultra-detailed"/"8K"
- 色彩: "cinematic color grading"/"teal-orange"/"desaturated"

### Layer 6: 时间线 (当视频≥8秒时使用)
格式: [0-Ns] 描述
按自然节奏分段,每段2-5秒

## 关键规则
1. **只输出优化后的提示词**,不要解释、不要"优化后:"前缀、不要引号
2. 保留用户核心意图,不改变内容方向
3. 中文输入→中文输出,英文输入→英文输出
4. 控制在150-500字(短视频150-250字,长视频300-500字)
5. 结尾添加负面约束: "Avoid: blurry, distorted faces, watermark, jerky movement"
6. 如果用户prompt已经很专业(>150字且含镜头术语),只做微调补充"""


def enhance_video_prompt(user_prompt, duration=5, ratio="16:9", resolution="720p"):
    """将大白话转为专业视频提示词

    Args:
        user_prompt: 用户原始描述
        duration: 视频时长(秒)
        ratio: 宽高比
        resolution: 分辨率

    Returns:
        dict: {"original": str, "enhanced": str, "method": "llm"|"rule"}
    """
    original = user_prompt.strip()

    # 如果已经很专业(长度>200且含镜头术语),只做微调
    is_professional = len(original) > 200 and _has_pro_terms(original)
    if is_professional:
        print("  📝 检测到专业prompt,仅微调补充")

    # 构建增强上下文
    context = f"视频参数: {duration}秒, {ratio}, {resolution}"
    if duration >= 8:
        context += "\n请添加时间分段 [0-Ns] 格式"

    llm_input = f"{context}\n\n用户描述:\n{original}"

    # LLM 增强
    enhanced = _call_llm(VIDEO_SYSTEM_PROMPT, llm_input, max_tokens=1500)

    if enhanced:
        # 清理 LLM 输出
        enhanced = _clean_llm_output(enhanced)
        return {"original": original, "enhanced": enhanced, "method": "llm"}

    # Fallback: 规则增强
    enhanced = _rule_enhance_video(original, duration)
    return {"original": original, "enhanced": enhanced, "method": "rule"}


def _rule_enhance_video(prompt, duration):
    """规则增强 (LLM不可用时的fallback)"""
    is_cn = any("\u4e00" <= c <= "\u9fff" for c in prompt[:20])

    if is_cn:
        additions = []
        if "特写" not in prompt and "全景" not in prompt and "中景" not in prompt:
            additions.append("电影级画面质感")
        if "光" not in prompt and "阳" not in prompt:
            additions.append("自然柔和的光线,丰富的光影层次")
        if "镜头" not in prompt:
            additions.append("镜头缓缓推近,捕捉细节")
        additions.append("cinematic, high dynamic range, 4K ultra-detailed")
        additions.append("Avoid: blurry, distorted, watermark, jerky movement")
        return prompt + "。" + "，".join(additions[:3]) + "。" + "。".join(additions[3:])
    else:
        additions = []
        if "shot" not in prompt.lower() and "close" not in prompt.lower():
            additions.append("Cinematic medium shot")
        if "light" not in prompt.lower():
            additions.append("natural cinematic lighting with volumetric rays")
        additions.append("shot on Arri Alexa, 35mm lens, shallow depth of field")
        additions.append("Avoid: blurry, distorted faces, watermark, jerky movement")
        return prompt + ". " + ". ".join(additions)


# ============================================================
# 图片 Prompt 增强
# ============================================================

IMAGE_SYSTEM_PROMPT = """你是世界顶级的AI图片创作导演。你的唯一任务是将用户的简单描述转化为Seedream 5.0能生成高质量图片的专业提示词。

## 你的输出必须包含以下五层结构（自然融合）

### Layer 1: 主体精确描述
- 将模糊主体精确化: 外貌、服装、材质、纹理、颜色
- 添加情感/状态: 表情、姿态、动作定格
- 例: "一只猫" → "一只毛发蓬松的奶油色英短猫,圆圆的铜色大眼睛,粉色鼻头,前爪优雅地交叠,端正地坐在天鹅绒垫子上"

### Layer 2: 风格规格
选择并明确一种视觉风格:
- 写实: "photorealistic, commercial photography quality"
- 电影: "cinematic still frame, movie poster quality"
- 插画: "digital illustration, concept art quality"
- 3D: "3D render, Pixar-style, octane render"
- 特殊: "oil painting, watercolor, ink wash, ukiyo-e"

### Layer 3: 构图指导
- 构图: "rule of thirds"/"symmetrical composition"/"centered subject"
- 视角: "eye-level"/"low-angle hero shot"/"bird's-eye view"/"overhead flat lay"
- 距离: "extreme close-up"/"portrait framing"/"full-body shot"/"wide environmental"

### Layer 4: 光影指令 (Seedream对光影高度敏感)
必须包含至少1-2项:
- "golden hour warm lighting"/"dramatic Rembrandt lighting"/"soft diffused studio light"
- "volumetric god rays"/"rim lighting creating silhouette"/"neon glow"
- "high contrast"/"moody low-key"/"bright and airy high-key"

### Layer 5: 技术参数
- 镜头: "shot on 85mm lens"/"35mm wide angle"/"macro lens"
- 景深: "shallow depth of field with creamy bokeh"/"deep focus"
- 质量: "8K ultra-detailed"/"high resolution"/"fine texture detail"

## 关键规则
1. **只输出优化后的提示词**,不要解释、不要前缀
2. 中文输入→中文输出为主,可夹杂英文技术术语
3. 控制在50-150字 (Seedream最佳区间30-100词)
4. 最重要的元素放在最前面 (Seedream对顺序敏感)
5. 保留用户核心意图
6. 如果用户prompt已很专业(>80字且含风格/光影),只做微调"""


def enhance_image_prompt(user_prompt, engine="seedream5", size="2K"):
    """将大白话转为专业图片提示词

    Args:
        user_prompt: 用户原始描述
        engine: 图片引擎
        size: 输出尺寸

    Returns:
        dict: {"original": str, "enhanced": str, "method": "llm"|"rule"}
    """
    original = user_prompt.strip()

    # 已经很专业
    is_professional = len(original) > 80 and _has_pro_terms(original)
    if is_professional:
        print("  📝 检测到专业prompt,仅微调补充")

    context = f"引擎: {engine}, 尺寸: {size}"
    llm_input = f"{context}\n\n用户描述:\n{original}"

    enhanced = _call_llm(IMAGE_SYSTEM_PROMPT, llm_input, max_tokens=600)

    if enhanced:
        enhanced = _clean_llm_output(enhanced)
        return {"original": original, "enhanced": enhanced, "method": "llm"}

    # Fallback: 规则增强
    enhanced = _rule_enhance_image(original, engine)
    return {"original": original, "enhanced": enhanced, "method": "rule"}


def _rule_enhance_image(prompt, engine):
    """规则增强 (LLM不可用时的fallback)"""
    is_cn = any("\u4e00" <= c <= "\u9fff" for c in prompt[:20])

    if is_cn:
        suffix = "，高清细腻，光影层次丰富，构图精美，色彩和谐，专业摄影级画质，8K超高清"
        if "风格" not in prompt and "画" not in prompt:
            suffix = "，电影级画面质感" + suffix
        return prompt + suffix
    else:
        suffix = ", cinematic composition, professional photography, detailed lighting, 8K ultra-detailed, high dynamic range"
        if "style" not in prompt.lower():
            suffix = ", photorealistic" + suffix
        return prompt + suffix


# ============================================================
# 辅助函数
# ============================================================

PRO_TERMS = [
    "cinematic", "tracking", "close-up", "wide shot", "dolly", "handheld",
    "volumetric", "rim light", "golden hour", "film grain", "Arri", "35mm", "85mm",
    "anamorphic", "IMAX", "shallow depth", "bokeh",
    "特写", "全景", "中景", "俯拍", "仰拍", "镜头", "运镜",
    "光影", "丁达尔", "轮廓光", "电影感", "一镜到底",
    "photorealistic", "8K", "4K", "cinematic color",
]


def _has_pro_terms(text):
    """检测文本是否已包含专业术语"""
    tl = text.lower()
    count = sum(1 for t in PRO_TERMS if t.lower() in tl)
    return count >= 3


def _clean_llm_output(text):
    """清理 LLM 输出中的杂质"""
    # 移除可能的前缀
    prefixes = [
        "优化后的提示词：", "优化后：", "Enhanced prompt:", "Optimized:",
        "以下是优化后的提示词：", "Here is the enhanced prompt:",
        "```", "---",
    ]
    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):]
    # 移除首尾引号
    text = text.strip().strip('"').strip("'").strip("`").strip()
    # 移除末尾的 ```
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prompt Enhancer — 大白话→专业提示词")
    parser.add_argument("--prompt", "-p", required=True, help="用户描述")
    parser.add_argument("--type", "-t", choices=["video", "image"], default="video", help="类型")
    parser.add_argument("--duration", type=int, default=5, help="视频时长")
    parser.add_argument("--ratio", default="16:9", help="视频比例")
    parser.add_argument("--engine", default="seedream5", help="图片引擎")
    parser.add_argument("--compare", action="store_true", help="并排对比原始/增强")

    args = parser.parse_args()

    if args.type == "video":
        print(f"🎬 视频 Prompt 增强 (duration={args.duration}s, ratio={args.ratio})")
        result = enhance_video_prompt(args.prompt, duration=args.duration, ratio=args.ratio)
    else:
        print(f"🎨 图片 Prompt 增强 (engine={args.engine})")
        result = enhance_image_prompt(args.prompt, engine=args.engine)

    print(f"\n📝 原始 ({len(result['original'])} chars):")
    print(f"  {result['original']}")
    print(f"\n✨ 增强 ({len(result['enhanced'])} chars, method={result['method']}):")
    print(f"  {result['enhanced']}")

    if args.compare:
        print(f"\n📊 增强比: {len(result['original'])} → {len(result['enhanced'])} ({len(result['enhanced'])/max(len(result['original']),1):.1f}x)")
