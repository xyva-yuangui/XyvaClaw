#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from pathlib import Path

JOBS_FILE = Path("/Users/momo/.openclaw/cron/jobs.json")


def main() -> int:
    if not JOBS_FILE.exists():
        print("❌ 未找到 cron/jobs.json")
        return 1

    data = json.loads(JOBS_FILE.read_text())
    jobs = data.get("jobs", [])
    enabled = [j for j in jobs if j.get("enabled")]

    print(f"总任务: {len(jobs)} | 启用: {len(enabled)} | 禁用: {len(jobs)-len(enabled)}")

    err_jobs = [j for j in enabled if j.get("state", {}).get("lastStatus") == "error"]
    if err_jobs:
        print("\n[高优先级] 失败任务:")
        for j in err_jobs:
            st = j.get("state", {})
            print(f"- {j.get('name')} ({j.get('id')}) errs={st.get('consecutiveErrors',0)} error={st.get('lastError','-')}")

    target_counter = Counter(j.get("sessionTarget", "-") for j in enabled)
    print("\nsessionTarget 分布:")
    for k, v in target_counter.items():
        print(f"- {k}: {v}")

    bad_target = [j for j in enabled if j.get("sessionTarget") != "isolated"]
    if bad_target:
        print("\n[建议] 以下任务建议改为 isolated:")
        for j in bad_target:
            print(f"- {j.get('name')} ({j.get('id')})")

    delivery_counter = Counter((j.get("delivery") or {}).get("mode", "none") for j in enabled)
    print("\ndelivery 分布:")
    for k, v in delivery_counter.items():
        print(f"- {k}: {v}")

    expr_map: dict[str, list[str]] = defaultdict(list)
    for j in enabled:
        schedule = j.get("schedule") or {}
        expr = schedule.get("expr") if schedule.get("kind") == "cron" else schedule.get("kind", "unknown")
        expr_map[str(expr)].append(j.get("name", j.get("id", "-")))

    collisions = {k: v for k, v in expr_map.items() if len(v) >= 2}
    if collisions:
        print("\n[建议] 频率完全相同可评估合并:")
        for expr, names in collisions.items():
            print(f"- {expr}: {', '.join(names)}")

    print("\n✅ 审计完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
