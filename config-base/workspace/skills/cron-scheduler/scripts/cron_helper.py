#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

JOBS_FILE = Path("~/.xyvaclaw/cron/jobs.json")


def shell(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def require_cli() -> None:
    if not shutil.which("openclaw"):
        raise RuntimeError("openclaw CLI 不可用，请先确认 PATH")


def load_jobs() -> list[dict]:
    if not JOBS_FILE.exists():
        return []
    data = json.loads(JOBS_FILE.read_text())
    return data.get("jobs", [])


def cmd_status(_: argparse.Namespace) -> int:
    jobs = load_jobs()
    enabled = [j for j in jobs if j.get("enabled")]
    failed = [j for j in jobs if j.get("state", {}).get("lastStatus") == "error"]
    print(f"jobs={len(jobs)} enabled={len(enabled)} failed={len(failed)}")
    for j in sorted(jobs, key=lambda x: x.get("name", ""))[:50]:
        st = j.get("state", {})
        print(
            f"- {j.get('id')} | {j.get('name')} | enabled={j.get('enabled')} | "
            f"last={st.get('lastStatus', 'idle')} | errs={st.get('consecutiveErrors', 0)}"
        )
    return 0


def cmd_failures(_: argparse.Namespace) -> int:
    jobs = load_jobs()
    failures = [
        j for j in jobs if (j.get("state", {}).get("lastStatus") == "error" or j.get("state", {}).get("consecutiveErrors", 0) > 0)
    ]
    if not failures:
        print("✅ 当前无失败cron")
        return 0
    print(f"⚠️ 失败/告警任务: {len(failures)}")
    for j in failures:
        st = j.get("state", {})
        print(
            f"- {j.get('id')} | {j.get('name')} | last={st.get('lastStatus')} | "
            f"errs={st.get('consecutiveErrors', 0)} | error={st.get('lastError', '-') }"
        )
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    require_cli()
    cmd = ["openclaw", "cron", "create", "--name", args.name]

    if args.at:
        cmd += ["--at", args.at]
    else:
        cmd += ["--schedule", args.cron]

    cmd += ["--type", "agentTurn", "--message", args.message]
    cmd += ["--session-target", args.session_target]

    if args.delivery == "announce":
        cmd += ["--delivery", "announce"]
        if args.channel:
            cmd += ["--channel", args.channel]
        if args.to:
            cmd += ["--to", args.to]
    else:
        cmd += ["--delivery", "none"]

    if args.tz:
        cmd += ["--tz", args.tz]

    code, out = shell(cmd)
    print(out)
    return code


def cmd_enable(args: argparse.Namespace) -> int:
    require_cli()
    code, out = shell(["openclaw", "cron", "enable", args.id])
    print(out)
    return code


def cmd_disable(args: argparse.Namespace) -> int:
    require_cli()
    code, out = shell(["openclaw", "cron", "disable", args.id])
    print(out)
    return code


def cmd_run(args: argparse.Namespace) -> int:
    require_cli()
    code, out = shell(["openclaw", "cron", "run", args.id])
    print(out)
    return code


def cmd_remove(args: argparse.Namespace) -> int:
    require_cli()
    code, out = shell(["openclaw", "cron", "remove", args.id])
    print(out)
    return code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cron helper for OpenClaw")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("failures")

    c = sub.add_parser("create")
    c.add_argument("--name", required=True)
    schedule_group = c.add_mutually_exclusive_group(required=True)
    schedule_group.add_argument("--cron", help="cron expression, e.g. 0 9 * * *")
    schedule_group.add_argument("--at", help="ISO timestamp, e.g. 2026-03-15T01:00:00Z")
    c.add_argument("--message", required=True)
    c.add_argument("--session-target", default="isolated", choices=["isolated", "main"])
    c.add_argument("--delivery", default="none", choices=["none", "announce"])
    c.add_argument("--channel", default="feishu")
    c.add_argument("--to", default="")
    c.add_argument("--tz", default="Asia/Shanghai")

    e = sub.add_parser("enable")
    e.add_argument("--id", required=True)

    d = sub.add_parser("disable")
    d.add_argument("--id", required=True)

    r = sub.add_parser("run")
    r.add_argument("--id", required=True)

    rm = sub.add_parser("remove")
    rm.add_argument("--id", required=True)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "status": cmd_status,
        "failures": cmd_failures,
        "create": cmd_create,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "run": cmd_run,
        "remove": cmd_remove,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
