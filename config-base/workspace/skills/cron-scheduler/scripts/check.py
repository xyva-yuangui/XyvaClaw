#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def main() -> int:
    print("🔍 检查 cron-scheduler 技能...")
    skill_dir = Path(__file__).resolve().parent.parent

    ok = True
    for rel in ["SKILL.md", "_meta.json", "scripts/cron_helper.py", "scripts/cron_audit.py"]:
        p = skill_dir / rel
        if p.exists():
            print(f"  ✅ {rel}")
        else:
            print(f"  ❌ {rel} 缺失")
            ok = False

    if shutil.which("openclaw"):
        print("  ✅ openclaw CLI")
        code, out = run(["openclaw", "cron", "list"])
        if code == 0:
            print("  ✅ openclaw cron list 可用")
        else:
            print("  ⚠️ openclaw cron list 调用失败")
            print(f"     {out[:200]}")
    else:
        print("  ⚠️ openclaw CLI 不在 PATH")

    if ok:
        print("\n🎉 cron-scheduler 技能检查通过")
        return 0
    print("\n🚨 cron-scheduler 技能检查失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
