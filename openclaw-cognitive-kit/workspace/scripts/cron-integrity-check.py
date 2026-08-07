#!/usr/bin/env python3
"""
cron 引用完整性巡检 —— 防止"任务在跑但脚本已不存在"的假绿灯复发

背景: cron 的 payload 是 agentTurn 自然语言（"运行 python3 xxx.py"）。
脚本不存在时 agent 只是把"找不到文件"当文本汇报，cron 本身仍记为 ok，
导致任务功能全死而监控面板一片绿。本脚本直接校验引用的文件是否存在。

同时校验：
  - 引用的脚本/技能文件是否存在
  - timeoutSeconds 是否明显小于该任务的历史实测耗时（会被截断）
  - 是否残留未替换的占位符（如飞书 ID 未填导致投递失败）

用法:
    python3 cron-integrity-check.py            # 人读报告
    python3 cron-integrity-check.py --json     # 机器可读
退出码: 0 = 全部健康 / 1 = 发现问题（可供上层告警）
"""
import json
import os
import re
import sys
from pathlib import Path

OPENCLAW = Path(os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.openclaw")))
JOBS = OPENCLAW / "cron" / "jobs.json"

SCRIPT_RE = re.compile(r'~/\.openclaw/([\w\-./]+\.(?:py|sh|mjs|js))')
PLACEHOLDER_RE = re.compile(r'YOUR_[A-Z_]+')


def check() -> dict:
    if not JOBS.is_file():
        return {"ok": False, "error": f"jobs.json 不存在: {JOBS}", "issues": []}
    try:
        data = json.loads(JOBS.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": f"jobs.json 无法解析: {e}", "issues": []}

    issues = []
    jobs = data.get("jobs", [])
    for j in jobs:
        name = j.get("name", "(未命名)")
        enabled = bool(j.get("enabled"))
        payload = json.dumps(j.get("payload", {}), ensure_ascii=False)
        state = j.get("state", {})

        # 1) 引用的脚本是否存在
        for m in SCRIPT_RE.finditer(payload):
            rel = m.group(1)
            if not (OPENCLAW / rel).exists():
                issues.append({
                    "job": name, "enabled": enabled, "kind": "missing_script",
                    "detail": f"引用的文件不存在: ~/.openclaw/{rel}",
                })

        # 2) 超时是否小于历史实测耗时（说明会被截断）
        to = j.get("payload", {}).get("timeoutSeconds")
        dur_ms = state.get("lastDurationMs")
        if enabled and to and dur_ms and dur_ms / 1000 >= to * 0.95:
            issues.append({
                "job": name, "enabled": enabled, "kind": "timeout_too_tight",
                "detail": f"timeout={to}s 但实测耗时 {round(dur_ms/1000)}s，可能被截断",
            })

        # 3) 投递目标残留占位符
        delivery = json.dumps(j.get("delivery", {}), ensure_ascii=False)
        for m in PLACEHOLDER_RE.finditer(delivery + payload):
            issues.append({
                "job": name, "enabled": enabled, "kind": "unfilled_placeholder",
                "detail": f"存在未填占位符 {m.group(0)}，投递或权限会失效",
            })

        # 4) 连续失败
        errs = state.get("consecutiveErrors", 0)
        if enabled and errs >= 3:
            issues.append({
                "job": name, "enabled": enabled, "kind": "repeated_failure",
                "detail": f"连续失败 {errs} 次，lastStatus={state.get('lastRunStatus')}",
            })

    # 去重（同一 job 同一问题只报一次）
    seen = set()
    uniq = []
    for i in issues:
        key = (i["job"], i["kind"], i["detail"])
        if key not in seen:
            seen.add(key)
            uniq.append(i)

    return {
        "ok": len(uniq) == 0,
        "total_jobs": len(jobs),
        "enabled_jobs": sum(1 for j in jobs if j.get("enabled")),
        "issues": uniq,
    }


def main():
    r = check()
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)

    print("🔍 cron 引用完整性巡检")
    if r.get("error"):
        print(f"❌ {r['error']}")
        sys.exit(1)
    print(f"   任务总数 {r['total_jobs']}（启用 {r['enabled_jobs']}）")
    if r["ok"]:
        print("✅ 未发现问题：所有引用的脚本存在、超时充足、无未填占位符、无连续失败")
        sys.exit(0)
    print(f"❌ 发现 {len(r['issues'])} 个问题:")
    for i in r["issues"]:
        flag = "启用中" if i["enabled"] else "已禁用"
        print(f"   [{flag}] {i['job']}")
        print(f"          {i['kind']}: {i['detail']}")
    sys.exit(1)


if __name__ == "__main__":
    main()
