#!/usr/bin/env python3
"""
syscontrol.py — macOS 系统控制：执行命令、管理进程、应用操作、文件系统。

用法:
    python3 syscontrol.py run "ls -la"
    python3 syscontrol.py run "pip install requests" --timeout 60
    python3 syscontrol.py ps [--name chrome]
    python3 syscontrol.py kill --pid 1234
    python3 syscontrol.py kill --name "Google Chrome"
    python3 syscontrol.py open /path/to/file
    python3 syscontrol.py open https://example.com
    python3 syscontrol.py notify "标题" "消息内容"
    python3 syscontrol.py disk
    python3 syscontrol.py --check
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MAX_OUTPUT_CHARS = 20000
DEFAULT_TIMEOUT = 30


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def cmd_run(command: str, timeout: int = DEFAULT_TIMEOUT,
            workdir: str = None, shell: str = "/bin/zsh") -> dict:
    """执行 shell 命令，返回 stdout/stderr/exit_code。"""
    start = time.monotonic()
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(Path.home()),
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout[:MAX_OUTPUT_CHARS],
            "stderr": result.stderr[:MAX_OUTPUT_CHARS],
            "success": result.returncode == 0,
            "elapsed_ms": elapsed_ms,
            "timestamp": _now(),
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command, "exit_code": -1,
            "stdout": "", "stderr": f"超时: 命令执行超过 {timeout} 秒",
            "success": False, "elapsed_ms": timeout * 1000, "timestamp": _now(),
        }
    except Exception as e:
        return {
            "command": command, "exit_code": -1,
            "stdout": "", "stderr": str(e),
            "success": False, "elapsed_ms": 0, "timestamp": _now(),
        }


def cmd_ps(name_filter: str = None) -> list:
    """列出当前运行进程，可按名称过滤。"""
    try:
        r = subprocess.run(
            ["ps", "-axo", "pid,ppid,%cpu,%mem,comm"],
            capture_output=True, text=True, timeout=10,
        )
        procs = []
        for line in r.stdout.strip().splitlines()[1:]:
            parts = line.split(None, 4)
            if len(parts) < 5:
                continue
            pid, ppid, cpu, mem, comm = parts
            if name_filter and name_filter.lower() not in comm.lower():
                continue
            procs.append({
                "pid": int(pid), "ppid": int(ppid),
                "cpu": float(cpu), "mem": float(mem),
                "name": comm.strip(),
            })
        return sorted(procs, key=lambda p: p["cpu"], reverse=True)[:50]
    except Exception as e:
        return [{"error": str(e)}]


def cmd_kill(pid: int = None, name: str = None, signal: str = "TERM") -> dict:
    """按 PID 或进程名终止进程。"""
    if pid:
        r = cmd_run(f"kill -{signal} {pid}", timeout=5)
        return {"target": f"pid={pid}", "signal": signal, "success": r["success"],
                "stderr": r["stderr"], "timestamp": _now()}
    elif name:
        r = cmd_run(f"pkill -{signal} -f \"{name}\"", timeout=5)
        return {"target": f"name={name}", "signal": signal, "success": r["success"],
                "stderr": r["stderr"], "timestamp": _now()}
    return {"error": "需要 --pid 或 --name"}


def cmd_open(target: str) -> dict:
    """用系统默认应用打开文件/URL/应用。"""
    r = cmd_run(f"open \"{target}\"", timeout=10)
    return {"target": target, "success": r["success"],
            "stderr": r.get("stderr", ""), "timestamp": _now()}


def cmd_notify(title: str, message: str, sound: bool = True) -> dict:
    """发送系统通知（macOS: osascript / Linux: notify-send）。"""
    sound_str = "default" if sound else ""
    # 通知实现分平台：macOS 用 osascript，Linux 用 notify-send
    if sys.platform == "darwin":
        script = f'display notification "{message}" with title "{title}"'
        if sound_str:
            script += f' sound name "{sound_str}"'
        r = cmd_run(f"osascript -e '{script}'", timeout=5)
    elif sys.platform.startswith("linux"):
        r = cmd_run(f'notify-send "{title}" "{message}"', timeout=5)
    else:
        r = {"success": False, "stderr": f"不支持的平台: {sys.platform}"}
    return {"title": title, "message": message, "success": r["success"],
            "stderr": r.get("stderr", ""), "timestamp": _now()}


def cmd_disk() -> dict:
    """获取磁盘使用情况。"""
    r = cmd_run("df -h", timeout=5)
    lines = r.get("stdout", "").strip().splitlines()
    disks = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 6:
            disks.append({
                "filesystem": parts[0], "size": parts[1],
                "used": parts[2], "avail": parts[3],
                "use_pct": parts[4], "mountpoint": parts[5],
            })
    return {"disks": disks, "raw": r.get("stdout", ""), "timestamp": _now()}


def cmd_env_set(key: str, value: str, persist: bool = False) -> dict:
    """设置环境变量（可选持久化到 ~/.zshenv）。"""
    os.environ[key] = value
    result = {"key": key, "value": value, "session": True, "persisted": False}
    if persist:
        zshenv = Path.home() / ".zshenv"
        line = f'\nexport {key}="{value}"\n'
        existing = zshenv.read_text(encoding="utf-8") if zshenv.exists() else ""
        # 替换已有的同名 export，或追加
        import re
        pattern = re.compile(rf'^export {re.escape(key)}=.*$', re.MULTILINE)
        if pattern.search(existing):
            new_content = pattern.sub(f'export {key}="{value}"', existing)
        else:
            new_content = existing + line
        zshenv.write_text(new_content, encoding="utf-8")
        result["persisted"] = True
        result["file"] = str(zshenv)
    return result


def health_check() -> dict:
    checks = [{"name": "python3", "status": "ok"}]
    for cmd_name, cmd in [("zsh", "zsh --version"), ("ps", "ps --version"),
                           ("osascript", "osascript -e 'return 1'")]:
        r = subprocess.run(cmd.split(), capture_output=True, timeout=5)
        checks.append({"name": cmd_name,
                        "status": "ok" if r.returncode == 0 else "warn"})
    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {"skill": "system-control", "version": "2.0.0",
            "status": overall, "checks": checks, "timestamp": _now()}


def main():
    parser = argparse.ArgumentParser(description="System Control")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="执行 shell 命令")
    p_run.add_argument("cmd", nargs="?", help="命令字符串")
    p_run.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_run.add_argument("--workdir", help="工作目录")

    p_ps = sub.add_parser("ps", help="列出进程")
    p_ps.add_argument("--name", help="按名称过滤")

    p_kill = sub.add_parser("kill", help="终止进程")
    p_kill.add_argument("--pid", type=int)
    p_kill.add_argument("--name")
    p_kill.add_argument("--signal", default="TERM", choices=["TERM", "KILL", "HUP", "INT"])

    p_open = sub.add_parser("open", help="打开文件/URL/应用")
    p_open.add_argument("target")

    p_notify = sub.add_parser("notify", help="macOS 系统通知")
    p_notify.add_argument("title")
    p_notify.add_argument("message")
    p_notify.add_argument("--no-sound", action="store_true")

    sub.add_parser("disk", help="磁盘使用情况")

    p_env = sub.add_parser("env-set", help="设置环境变量")
    p_env.add_argument("key")
    p_env.add_argument("value")
    p_env.add_argument("--persist", action="store_true", help="写入 ~/.zshenv")

    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    result = None
    if args.command == "run":
        if not args.cmd:
            parser.print_help()
            sys.exit(0)
        result = cmd_run(args.cmd, args.timeout, args.workdir)
        if not args.as_json:
            icon = "✅" if result["success"] else "❌"
            print(f"{icon} exit_code={result['exit_code']} ({result['elapsed_ms']}ms)")
            if result["stdout"]:
                print(result["stdout"])
            if result["stderr"]:
                print(f"STDERR: {result['stderr']}", file=sys.stderr)
    elif args.command == "ps":
        result = cmd_ps(args.name)
        if not args.as_json:
            print(f"{'PID':>8} {'CPU%':>6} {'MEM%':>6}  NAME")
            for p in (result if isinstance(result, list) else []):
                if "error" not in p:
                    print(f"{p['pid']:>8} {p['cpu']:>6.1f} {p['mem']:>6.1f}  {p['name']}")
    elif args.command == "kill":
        result = cmd_kill(args.pid, args.name, args.signal)
        if not args.as_json:
            icon = "✅" if result.get("success") else "❌"
            print(f"{icon} kill {result.get('target', '')} (signal={result.get('signal', '')})")
    elif args.command == "open":
        result = cmd_open(args.target)
        if not args.as_json:
            print(f"✅ 已打开: {args.target}" if result["success"] else f"❌ {result['stderr']}")
    elif args.command == "notify":
        result = cmd_notify(args.title, args.message, not args.no_sound)
        if not args.as_json:
            print(f"✅ 通知已发送" if result["success"] else f"❌ {result['stderr']}")
    elif args.command == "disk":
        result = cmd_disk()
        if not args.as_json:
            print(result.get("raw", ""))
    elif args.command == "env-set":
        result = cmd_env_set(args.key, args.value, args.persist)
        if not args.as_json:
            print(f"✅ {args.key}={args.value}" +
                  (f" (写入 {result.get('file','')})" if result.get("persisted") else ""))
    else:
        parser.print_help()
        sys.exit(0)

    if args.as_json and result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
