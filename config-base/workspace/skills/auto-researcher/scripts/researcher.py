#!/usr/bin/env python3
"""
Auto-Researcher — 自动化深度研究技能。
多轮搜索→信息提取→交叉验证→知识图谱存储→结构化报告。

Commands: research, track, survey
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path.home() / ".openclaw" / "workspace" / "skills"
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "researcher"
KG_SCRIPT = SKILLS_DIR / "knowledge-graph-memory" / "scripts" / "kg.py"
TRACKER_SCRIPT = SKILLS_DIR / "effect-tracker" / "scripts" / "tracker.py"
REASONING_SCRIPT = SKILLS_DIR / "deep-reasoning-chain" / "scripts" / "reason.py"


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _track(action, status="ok", latency_ms=None):
    if not TRACKER_SCRIPT.is_file():
        return
    cmd = [sys.executable, str(TRACKER_SCRIPT), "record",
           "--skill", "auto-researcher", "--action", action, "--status", status]
    if latency_ms:
        cmd += ["--latency-ms", str(latency_ms)]
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception:
        pass


def _kg_ingest(text):
    if not KG_SCRIPT.is_file():
        return
    try:
        subprocess.run([sys.executable, str(KG_SCRIPT), "ingest",
                        "--text", text[:2000]], capture_output=True, timeout=10)
    except Exception:
        pass


def _kg_query(query):
    if not KG_SCRIPT.is_file():
        return []
    try:
        r = subprocess.run([sys.executable, str(KG_SCRIPT), "query",
                            "--q", query, "--limit", "5", "--json"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return json.loads(r.stdout).get("results", [])
    except Exception:
        pass
    return []


def _ensure_dir(sub=""):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = OUTPUT_DIR / (f"{sub}_{ts}" if sub else ts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_research(topic: str, depth: str = "standard", sources: list = None,
                 max_rounds: int = 3, output_format: str = "markdown") -> dict:
    """Full research pipeline: decompose → multi-round search → extract → verify → report."""
    print(f"\n🔬 研究: {topic}")
    print(f"   深度: {depth} | 最大轮次: {max_rounds}")
    if sources:
        print(f"   指定来源: {', '.join(sources)}")
    print()

    out_dir = _ensure_dir(f"research_{topic[:20].replace(' ', '_')}")
    start = time.monotonic()

    # Step 1: Prior knowledge check
    prior = _kg_query(topic)
    if prior:
        print(f"  📚 知识图谱: {len(prior)} 条已有知识")

    # Step 2: Question decomposition
    print(f"  🧩 问题分解...")
    decomp_file = out_dir / "01_decomposition.md"
    with open(decomp_file, "w", encoding="utf-8") as f:
        f.write(f"# 研究分解: {topic}\n\n")
        f.write("## Agent 指令\n\n")
        f.write(f"使用 `deep-reasoning-chain decompose --question \"{topic}\"` 分解为子问题\n\n")
        f.write("## 推荐子问题方向\n\n")
        f.write(f"1. {topic} 的定义和范围\n")
        f.write(f"2. {topic} 的现状和最新进展\n")
        f.write(f"3. {topic} 的关键参与者/公司\n")
        f.write(f"4. {topic} 的优势和劣势\n")
        f.write(f"5. {topic} 的未来趋势和预测\n")
        if depth == "deep":
            f.write(f"6. {topic} 的定量数据和统计\n")
            f.write(f"7. {topic} 的对比分析（vs 竞品/替代方案）\n")
            f.write(f"8. {topic} 的案例研究\n")

    # Step 3: Multi-round search plan
    print(f"  🔍 搜索计划...")
    search_plan_file = out_dir / "02_search_plan.md"
    default_sources = sources or ["google", "bing", "scholar"]
    with open(search_plan_file, "w", encoding="utf-8") as f:
        f.write(f"# 搜索计划: {topic}\n\n")
        f.write(f"**轮次**: {max_rounds}\n")
        f.write(f"**搜索引擎**: {', '.join(default_sources)}\n\n")

        for round_num in range(1, max_rounds + 1):
            f.write(f"## 第 {round_num} 轮搜索\n\n")
            if round_num == 1:
                f.write("**目标**: 广度搜索，建立全貌\n")
                f.write("**查询**: \n")
                f.write(f"- `{topic} 综述 2026`\n")
                f.write(f"- `{topic} overview latest`\n")
                f.write(f"- `{topic} market report`\n\n")
            elif round_num == 2:
                f.write("**目标**: 深度搜索，验证关键发现\n")
                f.write("**查询**: [基于第1轮发现生成]\n\n")
            else:
                f.write("**目标**: 补充搜索，填补空白\n")
                f.write("**查询**: [基于前几轮的缺口]\n\n")

            f.write("### Agent 指令\n\n")
            f.write("```bash\n")
            f.write(f"# 使用 multi-search-engine 多引擎并行搜索\n")
            f.write(f"# 使用 web-scraper 提取搜索结果核心内容\n")
            f.write(f"# 使用 academic-deep-research 搜索学术文献 (如适用)\n")
            f.write("```\n\n")

    # Step 4: Information extraction template
    print(f"  📝 提取模板...")
    extract_file = out_dir / "03_extraction.md"
    with open(extract_file, "w", encoding="utf-8") as f:
        f.write(f"# 信息提取: {topic}\n\n")
        f.write("## 提取规则\n\n")
        f.write("从每个来源提取:\n")
        f.write("1. **核心观点** (≤3句话)\n")
        f.write("2. **关键数据** (数字、百分比、日期)\n")
        f.write("3. **来源可靠性** [1-5] (5=权威学术/政府, 1=匿名博客)\n")
        f.write("4. **时效性** (发布日期)\n\n")
        f.write("## 交叉验证\n\n")
        f.write("| 信息点 | 来源A | 来源B | 来源C | 一致? | 可信度 |\n")
        f.write("|--------|-------|-------|-------|------|--------|\n")
        f.write("| [关键发现1] | | | | | |\n")
        f.write("| [关键发现2] | | | | | |\n")

    # Step 5: Report template
    print(f"  📊 报告模板...")
    report_file = out_dir / "04_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# 研究报告: {topic}\n\n")
        f.write(f"**研究日期**: {_now()}\n")
        f.write(f"**研究深度**: {depth}\n")
        f.write(f"**搜索轮次**: {max_rounds}\n\n")
        f.write("---\n\n")

        f.write("## 摘要\n\n[Agent 填充: 200字以内核心发现]\n\n")
        f.write("## 1. 背景与定义\n\n[Agent 填充]\n\n")
        f.write("## 2. 现状分析\n\n[Agent 填充]\n\n")
        f.write("## 3. 关键发现\n\n")
        f.write("### 发现 1\n[Agent 填充]\n\n")
        f.write("### 发现 2\n[Agent 填充]\n\n")
        f.write("### 发现 3\n[Agent 填充]\n\n")

        if depth in ("standard", "deep"):
            f.write("## 4. 数据分析\n\n[Agent 填充: 表格/图表]\n\n")
            f.write("## 5. 对比分析\n\n[Agent 填充]\n\n")

        if depth == "deep":
            f.write("## 6. 案例研究\n\n[Agent 填充]\n\n")
            f.write("## 7. 专家观点\n\n[Agent 填充]\n\n")

        f.write("## 结论与建议\n\n[Agent 填充]\n\n")
        f.write("## 参考来源\n\n")
        f.write("| # | 来源 | 可靠性 | 日期 |\n")
        f.write("|---|------|--------|------|\n")
        f.write("| 1 | [Agent填充] | [?]/5 | |\n\n")

        f.write("---\n\n")
        f.write("## Agent 后续指令\n\n")
        f.write("1. 将关键发现存入 `knowledge-graph-memory`\n")
        f.write("2. 记录 `effect-tracker`\n")
        f.write("3. 如需推送报告: `smart-messenger` 发到飞书\n")

    elapsed_ms = int((time.monotonic() - start) * 1000)
    _track("research", "ok", elapsed_ms)
    _kg_ingest(f"研究主题: {topic}, 深度: {depth}")

    result = {
        "topic": topic, "depth": depth, "max_rounds": max_rounds,
        "sources": default_sources, "prior_knowledge": len(prior),
        "output_dir": str(out_dir), "elapsed_ms": elapsed_ms,
        "files": {
            "decomposition": str(decomp_file),
            "search_plan": str(search_plan_file),
            "extraction": str(extract_file),
            "report": str(report_file),
        },
        "timestamp": _now(),
    }

    with open(out_dir / "summary.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n  ✅ 研究框架已生成! ({elapsed_ms}ms)")
    print(f"  📂 {out_dir}")
    return result


def cmd_track(domain: str, keywords: list = None, interval: str = "weekly") -> dict:
    """Set up continuous domain tracking."""
    print(f"\n👁️ 领域追踪: {domain}")
    print(f"   关键词: {', '.join(keywords or [domain])}")
    print(f"   频率: {interval}")

    out_dir = _ensure_dir("track")

    track_config = {
        "domain": domain,
        "keywords": keywords or [domain],
        "interval": interval,
        "sources": ["google-scholar", "arxiv", "miniflux", "reddit"],
        "created_at": _now(),
        "status": "active",
    }

    config_file = out_dir / "track_config.json"
    with open(config_file, "w") as f:
        json.dump(track_config, f, indent=2, ensure_ascii=False)

    # Generate cron instruction
    cron_file = out_dir / "setup_cron.md"
    with open(cron_file, "w", encoding="utf-8") as f:
        f.write(f"# 设置定期追踪: {domain}\n\n")
        f.write("## Agent 指令\n\n")
        f.write(f"使用 `cron-mastery` 注册定时任务:\n\n")
        if interval == "daily":
            f.write(f"频率: 每天 08:00\n")
        elif interval == "weekly":
            f.write(f"频率: 每周一 09:00\n")
        else:
            f.write(f"频率: 每月1日 09:00\n")
        f.write(f"\n任务: 执行 researcher.py research --topic \"{domain}\" --depth quick\n")
        f.write(f"输出: 发送摘要到飞书 (smart-messenger)\n")

    _track("track_setup", "ok")
    print(f"  ✅ 追踪配置已生成: {config_file}")
    return track_config


def cmd_survey(domain: str, period: str = "weekly") -> dict:
    """Generate a domain survey/review."""
    print(f"\n📋 领域综述: {domain} ({period})")
    out_dir = _ensure_dir(f"survey_{domain[:15].replace(' ', '_')}")
    start = time.monotonic()

    survey_file = out_dir / "survey.md"
    with open(survey_file, "w", encoding="utf-8") as f:
        f.write(f"# {domain} — {'周' if period == 'weekly' else '月'}度综述\n\n")
        f.write(f"**生成时间**: {_now()}\n\n")

        f.write("## Agent 执行流程\n\n")
        f.write(f"1. 查询 KG: `kg.py query --q \"{domain}\" --since {period}`\n")
        f.write(f"2. 搜索最新进展: `multi-search-engine \"{domain} latest {period}\"`\n")
        f.write(f"3. 学术新文: `academic-deep-research --query \"{domain}\"`\n")
        f.write(f"4. 新闻聚合: `miniflux-news --search \"{domain}\"`\n\n")

        f.write("## 综述模板\n\n")
        f.write("### 本周要闻\n- [Agent 填充]\n\n")
        f.write("### 新研究/论文\n- [Agent 填充]\n\n")
        f.write("### 技术突破\n- [Agent 填充]\n\n")
        f.write("### 市场动态\n- [Agent 填充]\n\n")
        f.write("### 观点与预测\n- [Agent 填充]\n\n")
        f.write("### 总结\n- [Agent 填充]\n\n")

    elapsed_ms = int((time.monotonic() - start) * 1000)
    _track("survey", "ok", elapsed_ms)

    result = {"domain": domain, "period": period,
              "output_dir": str(out_dir), "elapsed_ms": elapsed_ms, "timestamp": _now()}

    with open(out_dir / "summary.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  📄 {survey_file}")
    return result


def health_check() -> dict:
    checks = [
        {"name": "knowledge-graph-memory", "status": "ok" if KG_SCRIPT.is_file() else "warn"},
        {"name": "effect-tracker", "status": "ok" if TRACKER_SCRIPT.is_file() else "warn"},
        {"name": "deep-reasoning-chain", "status": "ok" if REASONING_SCRIPT.is_file() else "warn"},
        {"name": "multi-search-engine",
         "status": "ok" if (SKILLS_DIR / "multi-search-engine-2.0.1" / "SKILL.md").is_file() else "warn"},
        {"name": "academic-deep-research",
         "status": "ok" if (SKILLS_DIR / "academic-deep-research-1.0.0" / "SKILL.md").is_file() else "warn"},
        {"name": "python3", "status": "ok"},
    ]
    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {"skill": "auto-researcher", "version": "1.0.0",
            "status": overall, "checks": checks, "timestamp": _now()}


def main():
    parser = argparse.ArgumentParser(description="Auto-Researcher")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")

    sub = parser.add_subparsers(dest="command")

    p_res = sub.add_parser("research", help="深度研究")
    p_res.add_argument("--topic", required=True)
    p_res.add_argument("--depth", default="standard", choices=["quick", "standard", "deep"])
    p_res.add_argument("--sources", help="逗号分隔来源")
    p_res.add_argument("--max-rounds", type=int, default=3)

    p_trk = sub.add_parser("track", help="领域追踪")
    p_trk.add_argument("--domain", required=True)
    p_trk.add_argument("--keywords", help="逗号分隔关键词")
    p_trk.add_argument("--interval", default="weekly", choices=["daily", "weekly", "monthly"])

    p_srv = sub.add_parser("survey", help="领域综述")
    p_srv.add_argument("--domain", required=True)
    p_srv.add_argument("--period", default="weekly", choices=["weekly", "monthly"])

    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    result = None
    if args.command == "research":
        srcs = [s.strip() for s in args.sources.split(",")] if args.sources else None
        result = cmd_research(args.topic, args.depth, srcs, args.max_rounds)
    elif args.command == "track":
        kws = [k.strip() for k in args.keywords.split(",")] if args.keywords else None
        result = cmd_track(args.domain, kws, args.interval)
    elif args.command == "survey":
        result = cmd_survey(args.domain, args.period)

    if args.json and result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
