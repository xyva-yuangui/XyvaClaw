#!/usr/bin/env python3
"""
send_message.py — Send templated messages to Feishu via OpenClaw gateway.

Usage:
    python3 send_message.py --chat <chat_id> --text "message"
    python3 send_message.py --chat <chat_id> --template <name> --vars '{"key": "val"}'
    python3 send_message.py --list-templates
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"


def load_gateway_config():
    """Read gateway port and auth token from openclaw.json."""
    if not OPENCLAW_CONFIG.exists():
        return {"port": 18789, "token": ""}
    try:
        cfg = json.loads(OPENCLAW_CONFIG.read_text(encoding="utf-8"))
        port = cfg.get("gateway", {}).get("port", 18789)
        token = cfg.get("gateway", {}).get("auth", {}).get("token", "")
        return {"port": port, "token": token}
    except (json.JSONDecodeError, KeyError):
        return {"port": 18789, "token": ""}


def list_templates():
    """List available message templates."""
    if not TEMPLATES_DIR.exists():
        print("No templates directory found.")
        return
    templates = sorted(TEMPLATES_DIR.glob("*.json"))
    if not templates:
        print("No templates found.")
        return
    for t in templates:
        try:
            data = json.loads(t.read_text(encoding="utf-8"))
            name = data.get("id", t.stem)
            desc = data.get("name", "")
            print(f"  {name:20s}  {desc}")
        except (json.JSONDecodeError, KeyError):
            print(f"  {t.stem:20s}  (invalid template)")


def load_template(name: str) -> dict:
    """Load a template by name."""
    path = TEMPLATES_DIR / f"{name}.json"
    if not path.exists():
        print(f"Template not found: {name}", file=sys.stderr)
        print(f"Available templates in: {TEMPLATES_DIR}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def render_template(template: dict, variables: dict) -> str:
    """Render a template with variable substitution."""
    card = template.get("card", {})
    header = card.get("header", {}).get("title", "")
    body = card.get("body", "")

    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        header = header.replace(placeholder, str(value))
        body = body.replace(placeholder, str(value))

    # Build Feishu interactive card JSON
    feishu_card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": header},
                "template": "blue",
            },
            "elements": [
                {"tag": "markdown", "content": body},
            ],
        },
    }
    return json.dumps(feishu_card, ensure_ascii=False)


def send_via_gateway(chat_id: str, content: str, msg_type: str = "text"):
    """Send message via OpenClaw gateway API."""
    gw = load_gateway_config()
    url = f"http://127.0.0.1:{gw['port']}/api/v1/messages"

    payload = {
        "target": f"chat:{chat_id}",
        "content": content,
        "type": msg_type,
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
    }
    if gw["token"]:
        headers["Authorization"] = f"Bearer {gw['token']}"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        return False
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        print("Is OpenClaw gateway running?", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Send messages to Feishu via OpenClaw")
    parser.add_argument("--chat", default="", help="Feishu chat ID")
    parser.add_argument("--text", default="", help="Plain text message")
    parser.add_argument("--template", default="", help="Template name")
    parser.add_argument("--vars", default="{}", help="Template variables as JSON string")
    parser.add_argument("--list-templates", action="store_true", help="List available templates")
    args = parser.parse_args()

    if args.list_templates:
        list_templates()
        return

    if not args.chat:
        print("Error: --chat is required", file=sys.stderr)
        sys.exit(1)

    if args.template:
        template = load_template(args.template)
        try:
            variables = json.loads(args.vars)
        except json.JSONDecodeError:
            print(f"Error: --vars must be valid JSON", file=sys.stderr)
            sys.exit(1)
        content = render_template(template, variables)
        success = send_via_gateway(args.chat, content, "interactive")
    elif args.text:
        content = json.dumps({"text": args.text}, ensure_ascii=False)
        success = send_via_gateway(args.chat, content, "text")
    else:
        print("Error: provide --text or --template", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
