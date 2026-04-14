#!/usr/bin/env python3
"""分析 Seedance 2.0 顶级 Prompt 模式 — 用于优化 prompt enhancer"""

import csv
import json
import sys
from collections import Counter
from pathlib import Path

CSV_PATH = Path.home() / "Downloads" / "seedance-2-0-prompts-20260414.csv"


def analyze():
    with open(CSV_PATH, "r") as f:
        rows = list(csv.DictReader(f))

    print(f"=== Seedance 2.0 Prompt 数据分析 ({len(rows)} prompts) ===\n")

    # 1. 长度分布
    lengths = [len(r.get("content", "")) for r in rows]
    print(f"Prompt长度: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)//len(lengths)}")
    buckets = {"<100": 0, "100-300": 0, "300-600": 0, "600-1000": 0, ">1000": 0}
    for l in lengths:
        if l < 100: buckets["<100"] += 1
        elif l < 300: buckets["100-300"] += 1
        elif l < 600: buckets["300-600"] += 1
        elif l < 1000: buckets["600-1000"] += 1
        else: buckets[">1000"] += 1
    print(f"长度分布: {json.dumps(buckets, ensure_ascii=False)}")

    # 2. 关键词模式统计
    camera_terms = [
        "tracking shot", "dolly", "close-up", "close up", "wide shot", "medium shot",
        "pan", "tilt", "crane", "steadicam", "handheld", "FPV", "orbit",
        "push-in", "push in", "pull-back", "pull back", "whip",
        "low-angle", "low angle", "high-angle", "high angle", "aerial", "macro",
        "extreme close", "bird's eye", "birds eye",
        "特写", "全景", "中景", "近景", "远景", "俯拍", "仰拍", "跟踪",
        "推近", "拉远", "平移", "摇臂", "手持", "鸟瞰", "低角度", "高角度",
    ]
    light_terms = [
        "golden hour", "rim light", "volumetric", "cinematic light", "dramatic light",
        "backlight", "neon", "chiaroscuro", "Rembrandt", "film grain", "lens flare",
        "bokeh", "ambient light", "studio light", "natural light", "silhouette",
        "丁达尔", "轮廓光", "逆光", "侧光", "柔光", "暖光", "冷光",
        "光影", "光效", "光晕", "光线", "阳光", "月光", "霓虹",
    ]
    style_terms = [
        "cinematic", "photorealistic", "hyper-realistic", "ultra-realistic",
        "Pixar", "anime", "2D animation", "3D animation", "IMAX", "anamorphic",
        "Arri", "35mm", "85mm", "24fps", "film noir", "documentary",
        "电影感", "写实", "超现实", "动画", "胶片", "CG", "4K", "8K",
    ]
    time_markers = [
        "[0", "[00:", "0-", "0–", "00–", "0:00", "0s]", "0s:",
        "第一镜", "第二镜", "第一部分", "第二部分",
        "TIMELINE", "timeline",
    ]

    cc = lc = sc = tc = 0
    for r in rows:
        c = r.get("content", "")
        cl = c.lower()
        if any(t.lower() in cl for t in camera_terms): cc += 1
        if any(t.lower() in cl for t in light_terms): lc += 1
        if any(t.lower() in cl for t in style_terms): sc += 1
        if any(t in c for t in time_markers): tc += 1

    print(f"\n📷 包含镜头语言: {cc}/{len(rows)} ({cc*100//len(rows)}%)")
    print(f"💡 包含光影描述: {lc}/{len(rows)} ({lc*100//len(rows)}%)")
    print(f"🎬 包含风格标签: {sc}/{len(rows)} ({sc*100//len(rows)}%)")
    print(f"⏱️  包含时间分段: {tc}/{len(rows)} ({tc*100//len(rows)}%)")

    # 3. 中英文分布
    cn_prompts = [r for r in rows if any("\u4e00" <= c <= "\u9fff" for c in r.get("content", "")[:20])]
    en_prompts = [r for r in rows if r not in cn_prompts]
    print(f"\n🌐 中文: {len(cn_prompts)}, 英文: {len(en_prompts)}")

    # 4. 提取高质量中文 prompt 模式
    print("\n" + "=" * 60)
    print("=== 高质量中文 Prompt 结构分析 (Top 5) ===")
    print("=" * 60)
    cn_sorted = sorted(cn_prompts, key=lambda r: len(r.get("content", "")), reverse=True)
    for r in cn_sorted[:5]:
        c = r["content"]
        print(f"\n--- ID={r['id']} {r['title'][:50]} (len={len(c)}) ---")
        print(c[:500])
        if len(c) > 500:
            print("...")

    # 5. 提取高质量英文 prompt 模式
    print("\n" + "=" * 60)
    print("=== 高质量英文 Prompt 结构分析 (Top 5) ===")
    print("=" * 60)
    en_sorted = sorted(en_prompts, key=lambda r: len(r.get("content", "")), reverse=True)
    for r in en_sorted[:5]:
        c = r["content"]
        print(f"\n--- ID={r['id']} {r['title'][:50]} (len={len(c)}) ---")
        print(c[:500])
        if len(c) > 500:
            print("...")

    # 6. 提取最常见的镜头/风格/技术词汇
    print("\n" + "=" * 60)
    print("=== 高频专业词汇 Top 20 ===")
    print("=" * 60)
    pro_terms = [
        "cinematic", "dramatic", "hyper-realistic", "ultra-realistic", "photorealistic",
        "close-up", "wide shot", "tracking", "dolly", "handheld", "slow motion",
        "golden hour", "rim light", "volumetric", "film grain", "lens flare",
        "shallow depth of field", "bokeh", "anamorphic", "Arri", "IMAX",
        "35mm", "85mm", "24fps", "8K", "4K", "continuous shot", "single take",
        "no cuts", "one shot", "Pixar", "anime",
        "电影感", "特写", "全景", "慢镜头", "一镜到底",
    ]
    term_counts = Counter()
    for r in rows:
        cl = r.get("content", "").lower()
        for t in pro_terms:
            if t.lower() in cl:
                term_counts[t] += 1
    for term, count in term_counts.most_common(25):
        print(f"  {term:30s} {count:4d} ({count*100//len(rows)}%)")

    # 7. 总结模式洞察
    print("\n" + "=" * 60)
    print("=== 核心洞察 ===")
    print("=" * 60)
    print("""
1. 最佳prompt长度: 200-600字 (占比最高的有效区间)
2. 镜头语言是必备要素 — 顶级prompt几乎都包含具体的镜头描述
3. 时间分段(time-coded)是长视频的标志性技巧
4. 光影/氛围描写是质量分水岭
5. 负面约束(negative prompt)出现在最专业的prompt中
6. 中文prompt偏好: 分镜脚本格式 + 角色设定 + 画质风格声明
7. 英文prompt偏好: 6-layer结构 + 技术参数 + 风格引用(导演/电影)
8. 顶级模式: FORMAT声明 → 主体描述 → 时间线分段 → 风格/技术 → 负面约束
""")


if __name__ == "__main__":
    analyze()
