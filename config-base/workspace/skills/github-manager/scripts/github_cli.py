#!/usr/bin/env python3
"""
GitHub Manager — GitHub API CLI
通过 GitHub REST API 管理 Repo/Issue/PR

用法:
  python3 github_cli.py repos --user USERNAME
  python3 github_cli.py issues --repo OWNER/REPO
  python3 github_cli.py create-issue --repo OWNER/REPO --title "Bug" --body "描述"
  python3 github_cli.py pr-list --repo OWNER/REPO
  python3 github_cli.py --check
"""
import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


def _github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    try:
        cfg = json.loads((Path.home() / ".openclaw" / "openclaw.json").read_text())
        return cfg.get("github", {}).get("token", "")
    except Exception:
        return ""


def _api(path: str, method: str = "GET", body: dict = None) -> dict:
    token = _github_token()
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OpenClaw"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    else:
        data = None
    req = urllib.request.Request(f"https://api.github.com{path}", data=data,
                                headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def cmd_repos(args):
    user = args.user
    data = _api(f"/users/{user}/repos?sort=updated&per_page=10")
    for r in data:
        stars = r.get("stargazers_count", 0)
        lang = r.get("language", "?")
        print(f"  ⭐{stars:<4} {r['full_name']:<40} [{lang}] {r.get('description', '')[:50]}")


def cmd_issues(args):
    data = _api(f"/repos/{args.repo}/issues?state=open&per_page=10")
    for i in data:
        if i.get("pull_request"):
            continue
        labels = ",".join(l["name"] for l in i.get("labels", []))
        print(f"  #{i['number']:<5} {i['title'][:60]:<60} [{labels}]")


def cmd_create_issue(args):
    body = {"title": args.title}
    if args.body:
        body["body"] = args.body
    if args.labels:
        body["labels"] = args.labels.split(",")
    r = _api(f"/repos/{args.repo}/issues", "POST", body)
    print(f"  ✅ Issue #{r['number']} created: {r['html_url']}")


def cmd_pr_list(args):
    data = _api(f"/repos/{args.repo}/pulls?state=open&per_page=10")
    for pr in data:
        print(f"  #{pr['number']:<5} {pr['title'][:60]:<60} by {pr['user']['login']}")


def health_check() -> dict:
    checks = []
    token = _github_token()
    checks.append({"name": "github-token", "status": "ok" if token else "info",
                   "message": "" if token else "未配置 (可选, GITHUB_TOKEN 或 github.token)"})
    try:
        _api("/rate_limit")
        checks.append({"name": "github-api", "status": "ok"})
    except Exception as e:
        checks.append({"name": "github-api", "status": "warn", "message": str(e)[:80]})
    fail = any(c["status"] == "fail" for c in checks)
    warn = any(c["status"] == "warn" for c in checks)
    overall = "fail" if fail else ("warn" if warn else "ok")
    return {"skill": "github-manager", "version": "2.0.0", "status": overall,
            "checks": checks, "timestamp": datetime.now().isoformat()}


def main():
    parser = argparse.ArgumentParser(description="GitHub Manager CLI")
    parser.add_argument("--check", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("repos")
    p.add_argument("--user", required=True)

    p = sub.add_parser("issues")
    p.add_argument("--repo", required=True)

    p = sub.add_parser("create-issue")
    p.add_argument("--repo", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body", default="")
    p.add_argument("--labels", default="")

    p = sub.add_parser("pr-list")
    p.add_argument("--repo", required=True)

    args = parser.parse_args()
    if args.check:
        r = health_check()
        print(json.dumps(r, indent=2, ensure_ascii=False))
        sys.exit(0 if r["status"] != "fail" else 1)
    if not args.cmd:
        parser.print_help()
        sys.exit(0)
    {"repos": cmd_repos, "issues": cmd_issues, "create-issue": cmd_create_issue,
     "pr-list": cmd_pr_list}[args.cmd](args)


if __name__ == "__main__":
    main()
