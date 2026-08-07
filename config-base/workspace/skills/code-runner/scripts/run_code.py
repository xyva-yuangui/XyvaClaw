#!/usr/bin/env python3
"""
Code Runner — 沙盒执行 Python / Shell 代码，返回结构化结果。

用法:
    python3 run_code.py --lang python --code "print('hello')"
    python3 run_code.py --lang python --file script.py --timeout 30
    python3 run_code.py --lang shell --code "ls -la"
    python3 run_code.py --lang shell --code "echo hi" --json
    python3 run_code.py --lang shell --code "rm -rf /tmp/x" --explain
    python3 run_code.py --lang python --code "df.head()" --session my_analysis
    python3 run_code.py --list-sessions
    python3 run_code.py --clear-session my_analysis
    python3 run_code.py --check
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "code-runner"
GUARD_LOG = Path.home() / ".openclaw" / "logs" / "code-runner-guard.log"
SESSION_DIR = Path.home() / ".openclaw" / "sessions" / "code-runner"
OPENCLAW_CFG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_TIMEOUT = 30
MAX_OUTPUT_CHARS = 10000
SESSION_TTL_SECONDS = 24 * 3600

_DANGEROUS_PATTERNS = [
    (r"rm\s+-[rRfFdI]*[rR][rRfFdI]*[\s$]",  "递归删除 (rm -r/-rf)",    "critical"),
    (r"dd\s+.*of=/dev/",                     "写裸块设备 (dd)",          "critical"),
    (r"\bmkfs\b",                            "格式化文件系统",           "critical"),
    (r"sudo\s+(rm|dd|mkfs|shred|wipefs)\b",  "sudo 危险命令",           "critical"),
    (r":\s*\(\)\s*\{\s*:.*\|.*:.*&",         "fork bomb",               "critical"),
    (r"\bshred\s+",                          "文件粉碎 (shred)",         "critical"),
    (r"\bwipefs\b",                          "擦除文件系统签名",         "critical"),
    (r">\s*/etc/(?!hosts\.d)",               "覆写系统配置文件",         "critical"),
    (r"mv\s+/[^\s]+\s+/[^\s]+",             "移动根级目录",            "high"),
    (r"chmod\s+[0-7]*[67][0-7]\s",           "宽松权限 (chmod 6xx/7xx)", "high"),
    (r"curl\b.*\|\s*(ba)?sh\b",              "管道执行远程脚本",         "high"),
    (r"wget\b.*-O\s*-.*\|\s*(ba)?sh\b",     "管道执行远程脚本",         "high"),
    (r"echo\s+.*>>\s*/etc/",                "追加写系统配置",           "high"),
    (r"crontab\s+-[ri]\b",                   "删除/替换 crontab",        "high"),
]


def _guard_shell(code: str, force: bool = False) -> dict:
    """检测 Shell 命令中的危险模式。critical 级始终拦截，high 级可用 --force 跳过。"""
    for pattern, label, level in _DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE | re.DOTALL):
            blocked = not (level == "high" and force)
            return {"safe": not blocked, "blocked": blocked, "level": level, "label": label}
    return {"safe": True, "blocked": False, "level": "ok", "label": ""}


def _log_guard(code: str, guard: dict) -> None:
    GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().isoformat(timespec="seconds")
    with open(GUARD_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{guard['level'].upper()}] {guard['label']} | {code[:120]}\n")


def _explain_shell(code: str) -> str:
    """调用 DeepSeek 解释 Shell 命令语义和风险（不执行命令）。"""
    import urllib.request
    try:
        cfg = json.loads(OPENCLAW_CFG.read_text(encoding="utf-8"))
        ds = cfg.get("models", {}).get("providers", {}).get("deepseek", {})
        api_key = ds.get("apiKey", "")
        base_url = ds.get("baseUrl", "https://api.deepseek.com/v1").rstrip("/")
    except Exception:
        return "⚠️ 读取 openclaw.json 失败"
    if not api_key:
        return "⚠️ 未配置 DeepSeek API Key，无法解释"
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是 Shell 命令专家。分析命令功能、潜在风险和副作用，回答简洁，中文。"},
            {"role": "user", "content": f"解释以下 Shell 命令：\n```sh\n{code}\n```\n\n请按格式回答：\n1. 功能：...\n2. 风险评级：low/medium/high/critical\n3. 注意事项：..."},
        ],
        "max_tokens": 400,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ 解释请求失败: {e}"


def _session_path(name: str) -> Path:
    return SESSION_DIR / f"{name}.json"


def _session_load(name: str) -> tuple:
    """返回 (codes: list[str], created_ts: float)，过期则返回空列表。"""
    p = _session_path(name)
    if not p.exists():
        return [], time.time()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        created = data.get("created", time.time())
        if time.time() - created > SESSION_TTL_SECONDS:
            p.unlink(missing_ok=True)
            return [], time.time()
        return data.get("codes", []), created
    except Exception:
        return [], time.time()


def _session_save(name: str, codes: list, created: float) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    _session_path(name).write_text(
        json.dumps({"name": name, "created": created,
                    "updated": time.time(), "codes": codes},
                   ensure_ascii=False),
        encoding="utf-8",
    )


def _session_list() -> list:
    if not SESSION_DIR.exists():
        return []
    result = []
    for f in sorted(SESSION_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            age_h = round((time.time() - data.get("created", 0)) / 3600, 1)
            result.append({
                "name": data.get("name", f.stem),
                "cells": len(data.get("codes", [])),
                "age_h": age_h,
                "expired": age_h > SESSION_TTL_SECONDS / 3600,
            })
        except Exception:
            pass
    return result


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def run_python(code: str, timeout: int = DEFAULT_TIMEOUT,
               workdir: str = None, env_vars: dict = None) -> dict:
    """在临时文件中执行 Python 代码，捕获 stdout/stderr/exit_code。"""
    start = time.monotonic()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                    delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name

    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(Path.home()),
            env=env,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stdout = result.stdout[:MAX_OUTPUT_CHARS]
        stderr = result.stderr[:MAX_OUTPUT_CHARS]
        return {
            "lang": "python",
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "success": result.returncode == 0,
            "elapsed_ms": elapsed_ms,
            "timeout": timeout,
            "timestamp": _now(),
        }
    except subprocess.TimeoutExpired:
        return {
            "lang": "python", "exit_code": -1,
            "stdout": "", "stderr": f"超时: 执行超过 {timeout} 秒",
            "success": False, "elapsed_ms": timeout * 1000,
            "timeout": timeout, "timestamp": _now(),
        }
    except Exception as e:
        return {
            "lang": "python", "exit_code": -1,
            "stdout": "", "stderr": str(e),
            "success": False, "elapsed_ms": 0,
            "timeout": timeout, "timestamp": _now(),
        }
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def run_python_session(code: str, session_name: str,
                       timeout: int = DEFAULT_TIMEOUT,
                       workdir: str = None, env_vars: dict = None) -> dict:
    """带会话记忆的 Python 执行：静默重放历史 cell，跨次保留变量和导入。"""
    prev_codes, created = _session_load(session_name)
    if prev_codes:
        prev_src = "\n".join(prev_codes)
        combined_lines = [
            "import sys as __sys, io as __io",
            "__null_io = __io.StringIO()",
            "__real_out, __real_err = __sys.stdout, __sys.stderr",
            "__sys.stdout, __sys.stderr = __null_io, __null_io",
            "try:",
            f"    exec({repr(prev_src)})",
            "except Exception:",
            "    pass",
            "finally:",
            "    __sys.stdout, __sys.stderr = __real_out, __real_err",
            "del __sys, __io, __null_io, __real_out, __real_err",
            "",
            code,
        ]
        combined = "\n".join(combined_lines)
    else:
        combined = code
    result = run_python(combined, timeout, workdir, env_vars)
    result["session"] = session_name
    result["session_cell"] = len(prev_codes) + 1
    _session_save(session_name, prev_codes + [code], created)
    return result


def run_shell(code: str, timeout: int = DEFAULT_TIMEOUT,
              workdir: str = None, env_vars: dict = None,
              force: bool = False) -> dict:
    """执行 Shell 命令/脚本，捕获 stdout/stderr/exit_code。内置危险命令拦截。"""
    guard = _guard_shell(code, force)
    if guard["blocked"]:
        _log_guard(code, guard)
        hint = ("critical 级命令无法强制执行。"
                if guard["level"] == "critical"
                else "使用 --force 参数可跳过此警告（high 级）。")
        return {
            "lang": "shell", "exit_code": -2,
            "stdout": "",
            "stderr": f"[{guard['level'].upper()}] 危险命令已拦截：{guard['label']}\n{hint}",
            "success": False, "elapsed_ms": 0,
            "timeout": timeout, "timestamp": _now(),
            "blocked": True, "guard_level": guard["level"],
        }
    start = time.monotonic()
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    try:
        result = subprocess.run(
            code,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir or str(Path.home()),
            env=env,
            executable="/bin/zsh",
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "lang": "shell",
            "exit_code": result.returncode,
            "stdout": result.stdout[:MAX_OUTPUT_CHARS],
            "stderr": result.stderr[:MAX_OUTPUT_CHARS],
            "success": result.returncode == 0,
            "elapsed_ms": elapsed_ms,
            "timeout": timeout,
            "timestamp": _now(),
        }
    except subprocess.TimeoutExpired:
        return {
            "lang": "shell", "exit_code": -1,
            "stdout": "", "stderr": f"超时: 执行超过 {timeout} 秒",
            "success": False, "elapsed_ms": timeout * 1000,
            "timeout": timeout, "timestamp": _now(),
        }
    except Exception as e:
        return {
            "lang": "shell", "exit_code": -1,
            "stdout": "", "stderr": str(e),
            "success": False, "elapsed_ms": 0,
            "timeout": timeout, "timestamp": _now(),
        }


def run_test(test_code: str, source_code: str = None,
             timeout: int = DEFAULT_TIMEOUT) -> dict:
    """运行 pytest 风格的测试代码，返回通过/失败数。"""
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        if source_code:
            (tmpdir_path / "source.py").write_text(source_code, encoding="utf-8")
        test_file = tmpdir_path / "test_code.py"
        test_file.write_text(test_code, encoding="utf-8")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "-v",
                 "--tb=short", "--no-header", "-q"],
                capture_output=True, text=True, timeout=timeout,
                cwd=tmpdir,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            stdout = result.stdout[:MAX_OUTPUT_CHARS]
            stderr = result.stderr[:MAX_OUTPUT_CHARS]

            passed = stdout.count(" PASSED")
            failed = stdout.count(" FAILED")
            errors = stdout.count(" ERROR")

            return {
                "lang": "python-test",
                "exit_code": result.returncode,
                "stdout": stdout, "stderr": stderr,
                "success": result.returncode == 0,
                "passed": passed, "failed": failed, "errors": errors,
                "elapsed_ms": elapsed_ms,
                "timestamp": _now(),
            }
        except subprocess.TimeoutExpired:
            return {
                "lang": "python-test", "exit_code": -1,
                "stdout": "", "stderr": f"测试超时: {timeout}s",
                "success": False, "passed": 0, "failed": 0, "errors": 0,
                "elapsed_ms": timeout * 1000, "timestamp": _now(),
            }
        except FileNotFoundError:
            return {
                "lang": "python-test", "exit_code": -1,
                "stdout": "", "stderr": "pytest 未安装，请运行: pip install pytest",
                "success": False, "passed": 0, "failed": 0, "errors": 0,
                "elapsed_ms": 0, "timestamp": _now(),
            }


def save_result(result: dict, label: str = "") -> Path:  # noqa: E302
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"run_{label}_{ts}.json" if label else f"run_{ts}.json"
    out = OUTPUT_DIR / fname
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def health_check() -> dict:
    checks = [
        {"name": "python3", "status": "ok"},
        {"name": "shell_guard", "status": "ok",
         "message": f"{len(_DANGEROUS_PATTERNS)} danger patterns"},
    ]
    try:
        subprocess.run([sys.executable, "-m", "pytest", "--version"],
                       capture_output=True, timeout=5)
        checks.append({"name": "pytest", "status": "ok"})
    except Exception:
        checks.append({"name": "pytest", "status": "warn",
                       "message": "pip install pytest"})
    result = run_shell("echo ok", timeout=5)
    checks.append({"name": "shell", "status": "ok" if result["success"] else "fail"})
    overall = "fail" if any(c["status"] == "fail" for c in checks) \
        else "warn" if any(c["status"] == "warn" for c in checks) else "ok"
    return {"skill": "code-runner", "version": "2.0.0",
            "status": overall, "checks": checks, "timestamp": _now()}


def _print_result(result: dict, as_json: bool):
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    icon = "✅" if result["success"] else "❌"
    print(f"\n{icon} exit_code={result['exit_code']} | {result['elapsed_ms']}ms")
    if result.get("stdout"):
        print("\n── stdout ──")
        print(result["stdout"])
    if result.get("stderr"):
        print("\n── stderr ──")
        print(result["stderr"])
    if "passed" in result:
        print(f"\n🧪 passed={result['passed']} failed={result['failed']} errors={result['errors']}")


def main():
    parser = argparse.ArgumentParser(description="Code Runner v2 — 带安全卫士和会话记忆")
    parser.add_argument("--lang", "-l", choices=["python", "shell", "test"],
                        default="python", help="执行语言")
    parser.add_argument("--code", "-c", help="内联代码字符串")
    parser.add_argument("--file", "-f", help="代码文件路径")
    parser.add_argument("--source", help="被测代码文件（与 --lang test 配合）")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--workdir", "-w", help="工作目录")
    parser.add_argument("--env", help='环境变量 JSON 字符串，如 \'{"KEY":"val"}\'')
    parser.add_argument("--save", action="store_true", help="保存结果到文件")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--check", action="store_true", help="健康检查")
    parser.add_argument("--explain", action="store_true",
                        help="解释 Shell 命令语义（不执行，仅限 --lang shell）")
    parser.add_argument("--force", action="store_true",
                        help="强制执行 high 级危险命令（critical 级不可跳过）")
    parser.add_argument("--session", metavar="NAME",
                        help="会话名称，跨次保留 Python 执行上下文（变量/导入）")
    parser.add_argument("--list-sessions", action="store_true", dest="list_sessions",
                        help="列出全部活跃会话")
    parser.add_argument("--clear-session", metavar="NAME", dest="clear_session",
                        help="清除指定会话")
    args = parser.parse_args()

    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)

    if args.list_sessions:
        sessions = _session_list()
        if not sessions:
            print("当前无活跃会话")
        else:
            # 表头字段先提出变量：f-string 表达式内不能含反斜杠（Python ≤3.11）
            _h_name, _h_cells, _h_age = "名称", "Cells", "存活时长"
            print(f"{_h_name:<20} {_h_cells:>5} {_h_age:>8}")
            print("-" * 38)
            for s in sessions:
                mark = " [已过期]" if s["expired"] else ""
                print(f"{s['name']:<20} {s['cells']:>5} {s['age_h']:>6.1f}h{mark}")
        sys.exit(0)

    if args.clear_session:
        p = _session_path(args.clear_session)
        if p.exists():
            p.unlink()
            print(f"✅ 已清除会话: {args.clear_session}")
        else:
            print(f"⚠️  会话不存在: {args.clear_session}")
        sys.exit(0)

    env_vars = json.loads(args.env) if args.env else None

    code = args.code
    if not code and args.file:
        code = Path(args.file).read_text(encoding="utf-8")
    if not code:
        parser.print_help()
        sys.exit(0)

    if args.explain:
        if args.lang != "shell":
            print("⚠️  --explain 仅支持 --lang shell")
            sys.exit(1)
        print(f"🔍 解释命令: {code[:80]}{'...' if len(code) > 80 else ''}")
        print()
        print(_explain_shell(code))
        sys.exit(0)

    if args.lang == "python":
        if args.session:
            result = run_python_session(code, args.session, args.timeout,
                                        args.workdir, env_vars)
        else:
            result = run_python(code, args.timeout, args.workdir, env_vars)
    elif args.lang == "shell":
        result = run_shell(code, args.timeout, args.workdir, env_vars,
                           force=args.force)
    elif args.lang == "test":
        source_code = Path(args.source).read_text(encoding="utf-8") if args.source else None
        result = run_test(code, source_code, args.timeout)
    else:
        parser.print_help()
        sys.exit(1)

    _print_result(result, args.as_json)

    if not args.as_json and args.session and "session_cell" in result:
        print(f"\n📦 会话: {result['session']} | cell #{result['session_cell']}")

    if args.save:
        out = save_result(result, args.lang)
        print(f"\n💾 已保存: {out}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
