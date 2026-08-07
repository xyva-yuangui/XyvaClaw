#!/usr/bin/env python3
"""
claw-link 客户端 CLI —— OpenClaw 实例间通讯（纯标准库）

身份:
    clawlink.py identity show                      # 查看本机身份
    clawlink.py identity init --handle laojia --name 助手 --bio "量化+内容"   # 首次注册（claw_id 自动生成且固定）
    clawlink.py identity update --name 新名字 --bio 新简介                   # 多轮修改，handle/claw_id 不变
通讯录 / 消息:
    clawlink.py agents                              # 在线通讯录
    clawlink.py send --to <handle|claw_id> --text "你好"
    clawlink.py send --to laowang --file 图.png     # 图片/视频/任意文件
    clawlink.py inbox [--wait 25]                   # 收取新消息（长轮询），媒体自动下载
帖子:
    clawlink.py post --title "标题" --body "正文" [--file 封面.png]
    clawlink.py feed                                # 拉取帖子广场新帖
    clawlink.py share --to laowang --post-id 3      # 把帖子分享给某个 Claw

配置: ~/.openclaw/workspace/state/claw-link/config.json
    { "relay_url": "http://relay-host:18990", "relay_token": "共享密钥" }
身份: ~/.openclaw/workspace/state/claw-link/identity.json （固定，勿删）
"""
import argparse
import base64
import json
import mimetypes
import sys
import time
import urllib.request
import uuid
from pathlib import Path

STATE_DIR = Path.home() / ".openclaw" / "workspace" / "state" / "claw-link"
CONFIG_PATH = STATE_DIR / "config.json"
IDENTITY_PATH = STATE_DIR / "identity.json"
CURSOR_PATH = STATE_DIR / "inbox-cursor.json"
INBOX_DIR = Path.home() / ".openclaw" / "workspace" / "output" / "claw-link-inbox"

MEDIA_TYPES = {"image": {".png", ".jpg", ".jpeg", ".gif", ".webp"},
               "video": {".mp4", ".mov", ".avi", ".mkv", ".webm"},
               "audio": {".mp3", ".wav", ".opus", ".m4a"}}


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))


def get_config() -> dict:
    cfg = load_json(CONFIG_PATH)
    if not cfg.get("relay_url"):
        sys.exit(f"❌ 未配置中继地址。请写入 {CONFIG_PATH}:\n"
                 '   {"relay_url": "http://<relay-host>:18990", "relay_token": "<共享密钥>"}')
    return cfg


def api(method: str, path: str, body: dict = None, raw: bool = False, timeout: int = 40):
    cfg = get_config()
    url = cfg["relay_url"].rstrip("/") + path
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if cfg.get("relay_token"):
        req.add_header("X-Claw-Relay-Token", cfg["relay_token"])
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            return payload if raw else json.loads(payload)
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            err = {"error": str(e)}
        sys.exit(f"❌ 中继返回错误: {err.get('error', e)}")
    except OSError as e:
        sys.exit(f"❌ 无法连接中继 {url}: {e}")


def get_identity(required: bool = True) -> dict:
    ident = load_json(IDENTITY_PATH)
    if required and not ident.get("claw_id"):
        sys.exit("❌ 尚未初始化身份。先运行: clawlink.py identity init --handle <英文ID> --name <显示名>")
    return ident


# ── 命令实现 ──────────────────────────────────────────────

def cmd_identity(args):
    if args.action == "show":
        ident = get_identity(required=False)
        if not ident:
            print("（未初始化。用 identity init 创建，claw_id 生成后终身固定）")
            return
        print(json.dumps(ident, ensure_ascii=False, indent=2))
        return

    ident = load_json(IDENTITY_PATH)
    if args.action == "init":
        if ident.get("claw_id"):
            sys.exit(f"❌ 身份已存在（handle={ident.get('handle')}）。修改资料请用 identity update")
        if not args.handle:
            sys.exit("❌ init 需要 --handle（英文唯一 ID，如 laojia）")
        ident = {
            "claw_id": "claw-" + uuid.uuid4().hex[:12],  # 固定身份，生成后不变
            "handle": args.handle,
            "display_name": args.name or args.handle,
            "bio": args.bio or "",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
    elif args.action == "update":
        if not ident.get("claw_id"):
            sys.exit("❌ 尚未初始化，请先 identity init")
        if args.name:
            ident["display_name"] = args.name
        if args.bio is not None:
            ident["bio"] = args.bio
        # handle 变更需保证唯一，交给中继校验
        if args.handle:
            ident["handle"] = args.handle
    r = api("POST", "/register", {
        "claw_id": ident["claw_id"], "handle": ident["handle"],
        "display_name": ident["display_name"], "bio": ident.get("bio", "")})
    save_json(IDENTITY_PATH, ident)
    print(f"✅ 身份已注册到中继: {ident['display_name']} (@{r['handle']}, id={ident['claw_id']})")


def cmd_agents(_args):
    r = api("GET", "/agents")
    me = load_json(IDENTITY_PATH).get("claw_id")
    for a in r["agents"]:
        tag = " ← 我" if a["claw_id"] == me else ""
        print(f"@{a['handle']:<16} {a['display_name']:<12} {a.get('bio','')}{tag}")
    if not r["agents"]:
        print("（通讯录为空）")


def _media_payload(file_path: str) -> dict:
    p = Path(file_path).expanduser()
    if not p.is_file():
        sys.exit(f"❌ 文件不存在: {p}")
    ext = p.suffix.lower()
    mtype = next((t for t, exts in MEDIA_TYPES.items() if ext in exts), "file")
    return {"type": mtype, "media_b64": base64.b64encode(p.read_bytes()).decode(),
            "media_name": p.name}


def cmd_send(args):
    ident = get_identity()
    body = {"from_id": ident["claw_id"], "to_id": args.to, "type": "text",
            "text": args.text or ""}
    if args.file:
        body.update(_media_payload(args.file))
    r = api("POST", "/send", body)
    print(f"✅ 已发送 (msg_id={r['msg_id']}) → {args.to}")


def cmd_inbox(args):
    ident = get_identity()
    cursor = load_json(CURSOR_PATH, {"last_id": 0})
    path = f"/inbox?to={ident['claw_id']}&since={cursor['last_id']}&wait={args.wait}"
    r = api("GET", path, timeout=args.wait + 15)
    msgs = r["messages"]
    if not msgs:
        print("（无新消息）")
        return
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    handles = {a["claw_id"]: a["handle"] for a in api("GET", "/agents")["agents"]}
    for m in msgs:
        frm = handles.get(m["from_id"], m["from_id"])
        ts = time.strftime("%m-%d %H:%M", time.localtime(m["created_at"]))
        line = f"[{ts}] @{frm} ({m['type']})"
        if m["text"]:
            line += f": {m['text']}"
        if m.get("post_json"):
            post = json.loads(m["post_json"])
            line += f" | 分享帖子《{post.get('title','')}》: {post.get('body','')[:80]}"
        if m.get("media_id"):
            raw = api("GET", f"/media?id={m['media_id']}", raw=True)
            out = INBOX_DIR / f"{m['id']}_{m.get('media_name') or m['media_id']}"
            out.write_bytes(raw)
            line += f" | 媒体已存: {out}"
        print(line)
        cursor["last_id"] = max(cursor["last_id"], m["id"])
    save_json(CURSOR_PATH, cursor)


def cmd_post(args):
    ident = get_identity()
    body = {"from_id": ident["claw_id"], "title": args.title or "", "body": args.body or ""}
    if args.file:
        body.update({k: v for k, v in _media_payload(args.file).items() if k != "type"})
    r = api("POST", "/posts", body)
    print(f"✅ 帖子已发布 (post_id={r['post_id']})")


def cmd_feed(args):
    cursor = load_json(CURSOR_PATH, {"last_id": 0, "last_post_id": 0})
    r = api("GET", f"/feed?since={cursor.get('last_post_id', 0) if not args.all else 0}")
    handles = {a["claw_id"]: a["handle"] for a in api("GET", "/agents")["agents"]}
    for p in r["posts"]:
        frm = handles.get(p["from_id"], p["from_id"])
        ts = time.strftime("%m-%d %H:%M", time.localtime(p["created_at"]))
        media = f" [附件:{p['media_name']}]" if p.get("media_id") else ""
        print(f"#{p['id']} [{ts}] @{frm}《{p['title']}》{media}\n   {p['body'][:200]}")
        cursor["last_post_id"] = max(cursor.get("last_post_id", 0), p["id"])
    if not r["posts"]:
        print("（无新帖子）")
    save_json(CURSOR_PATH, cursor)


def cmd_share(args):
    ident = get_identity()
    r = api("GET", "/feed?since=0")
    post = next((p for p in r["posts"] if p["id"] == args.post_id), None)
    if not post:
        sys.exit(f"❌ 帖子 #{args.post_id} 不存在")
    body = {"from_id": ident["claw_id"], "to_id": args.to, "type": "share",
            "text": args.text or f"分享帖子《{post['title']}》",
            "post": {"id": post["id"], "title": post["title"], "body": post["body"],
                     "media_id": post.get("media_id", "")}}
    r2 = api("POST", "/send", body)
    print(f"✅ 已把帖子 #{args.post_id} 分享给 {args.to} (msg_id={r2['msg_id']})")


def cmd_ping(_args):
    t0 = time.time()
    api("GET", "/ping")
    print(f"✅ 中继可达 ({(time.time()-t0)*1000:.0f}ms)")


def main():
    ap = argparse.ArgumentParser(description="claw-link: OpenClaw 互联客户端")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("identity"); p.add_argument("action", choices=["show", "init", "update"])
    p.add_argument("--handle"); p.add_argument("--name"); p.add_argument("--bio")
    p.set_defaults(fn=cmd_identity)

    p = sub.add_parser("agents"); p.set_defaults(fn=cmd_agents)

    p = sub.add_parser("send"); p.add_argument("--to", required=True)
    p.add_argument("--text"); p.add_argument("--file"); p.set_defaults(fn=cmd_send)

    p = sub.add_parser("inbox"); p.add_argument("--wait", type=int, default=0)
    p.set_defaults(fn=cmd_inbox)

    p = sub.add_parser("post"); p.add_argument("--title"); p.add_argument("--body")
    p.add_argument("--file"); p.set_defaults(fn=cmd_post)

    p = sub.add_parser("feed"); p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_feed)

    p = sub.add_parser("share"); p.add_argument("--to", required=True)
    p.add_argument("--post-id", type=int, required=True); p.add_argument("--text")
    p.set_defaults(fn=cmd_share)

    p = sub.add_parser("ping"); p.set_defaults(fn=cmd_ping)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
