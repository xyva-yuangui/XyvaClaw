#!/usr/bin/env python3
"""Email Tool — read, search, send emails via IMAP/SMTP.

Usage:
  python3 email_tool.py inbox --limit 10
  python3 email_tool.py search --from "user@example.com" --days 7
  python3 email_tool.py read --id 12345
  python3 email_tool.py send --to "user@example.com" --subject "Hi" --body "Content"
  python3 email_tool.py send --to "user@example.com" --subject "Report" --body "See attached" --attach report.pdf
  python3 email_tool.py download-attachments --id 12345 --output-dir ./attachments/
"""
from __future__ import annotations
import argparse, email, imaplib, os, smtplib, sys
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path

DEFAULT_OUTPUT_DIR = os.path.join(
    os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.xyvaclaw")),
    "workspace", "output", "email"
)


def _load_config() -> dict:
    """Load email config from environment or .env file."""
    config = {}
    keys = ["EMAIL_IMAP_HOST", "EMAIL_IMAP_PORT", "EMAIL_SMTP_HOST", "EMAIL_SMTP_PORT",
            "EMAIL_USER", "EMAIL_PASSWORD", "EMAIL_FROM"]

    # Try environment first
    for k in keys:
        v = os.environ.get(k)
        if v:
            config[k] = v

    # Fill from .env if missing
    if len(config) < 3:
        env_file = os.path.join(
            os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.xyvaclaw")),
            ".env"
        )
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k in keys and k not in config:
                            config[k] = v

    required = ["EMAIL_IMAP_HOST", "EMAIL_USER", "EMAIL_PASSWORD"]
    missing = [k for k in required if k not in config]
    if missing:
        sys.exit(f"Missing email config: {', '.join(missing)}\nAdd them to .env or set as environment variables.")

    config.setdefault("EMAIL_IMAP_PORT", "993")
    config.setdefault("EMAIL_SMTP_HOST", config["EMAIL_IMAP_HOST"].replace("imap", "smtp"))
    config.setdefault("EMAIL_SMTP_PORT", "587")
    config.setdefault("EMAIL_FROM", config["EMAIL_USER"])

    return config


def _decode_str(s):
    """Decode email header string."""
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for data, charset in parts:
        if isinstance(data, bytes):
            result.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(str(data))
    return " ".join(result)


def _get_body(msg) -> str:
    """Extract text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        # Fallback to HTML
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return f"[HTML]\n{payload.decode(charset, errors='replace')}"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _connect_imap(config: dict) -> imaplib.IMAP4_SSL:
    """Connect to IMAP server."""
    imap = imaplib.IMAP4_SSL(config["EMAIL_IMAP_HOST"], int(config["EMAIL_IMAP_PORT"]))
    imap.login(config["EMAIL_USER"], config["EMAIL_PASSWORD"])
    return imap


def inbox(limit: int = 10):
    """List recent emails from inbox."""
    config = _load_config()
    imap = _connect_imap(config)
    imap.select("INBOX", readonly=True)

    _, data = imap.search(None, "ALL")
    ids = data[0].split()
    recent_ids = ids[-limit:] if len(ids) > limit else ids
    recent_ids.reverse()

    for uid in recent_ids:
        _, msg_data = imap.fetch(uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject = _decode_str(msg.get("Subject", ""))
        sender = _decode_str(msg.get("From", ""))
        date = msg.get("Date", "")
        print(f"  ID: {uid.decode()}  From: {sender}")
        print(f"  Subject: {subject}")
        print(f"  Date: {date}")
        print()

    imap.close()
    imap.logout()
    print(f"--- {len(recent_ids)} emails ---")


def search_emails(from_addr: str | None = None, subject: str | None = None, days: int = 7):
    """Search emails by criteria."""
    config = _load_config()
    imap = _connect_imap(config)
    imap.select("INBOX", readonly=True)

    criteria = []
    if from_addr:
        criteria.append(f'FROM "{from_addr}"')
    if subject:
        criteria.append(f'SUBJECT "{subject}"')
    if days:
        since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        criteria.append(f'SINCE {since}')

    search_str = " ".join(criteria) if criteria else "ALL"
    _, data = imap.search(None, search_str)
    ids = data[0].split()

    for uid in ids[-20:]:
        _, msg_data = imap.fetch(uid, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        print(f"  ID: {uid.decode()}  From: {_decode_str(msg.get('From', ''))}")
        print(f"  Subject: {_decode_str(msg.get('Subject', ''))}")
        print()

    imap.close()
    imap.logout()
    print(f"--- {len(ids)} results ---")


def read_email(email_id: str):
    """Read a specific email by ID."""
    config = _load_config()
    imap = _connect_imap(config)
    imap.select("INBOX", readonly=True)

    _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
    if not msg_data or not msg_data[0]:
        sys.exit(f"Email {email_id} not found")

    msg = email.message_from_bytes(msg_data[0][1])
    print(f"From: {_decode_str(msg.get('From', ''))}")
    print(f"To: {_decode_str(msg.get('To', ''))}")
    print(f"Subject: {_decode_str(msg.get('Subject', ''))}")
    print(f"Date: {msg.get('Date', '')}")
    print(f"---")
    print(_get_body(msg))

    # List attachments
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                print(f"\n📎 Attachment: {_decode_str(filename)}")

    imap.close()
    imap.logout()


def send_email(to: str, subject: str, body: str, attach: str | None = None, html: bool = False):
    """Send an email."""
    config = _load_config()

    msg = MIMEMultipart()
    msg["From"] = config["EMAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject

    content_type = "html" if html else "plain"
    msg.attach(MIMEText(body, content_type, "utf-8"))

    if attach and os.path.exists(attach):
        with open(attach, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attach)}")
            msg.attach(part)

    port = int(config["EMAIL_SMTP_PORT"])
    if port == 465:
        server = smtplib.SMTP_SSL(config["EMAIL_SMTP_HOST"], port)
    else:
        server = smtplib.SMTP(config["EMAIL_SMTP_HOST"], port)
        server.starttls()

    server.login(config["EMAIL_USER"], config["EMAIL_PASSWORD"])
    server.send_message(msg)
    server.quit()

    print(f"✅ Email sent to {to}: {subject}")


def download_attachments(email_id: str, output_dir: str):
    """Download attachments from an email."""
    config = _load_config()
    imap = _connect_imap(config)
    imap.select("INBOX", readonly=True)

    _, msg_data = imap.fetch(email_id.encode(), "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    os.makedirs(output_dir, exist_ok=True)
    count = 0
    if msg.is_multipart():
        for part in msg.walk():
            filename = part.get_filename()
            if filename:
                filename = _decode_str(filename)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                print(f"  📎 Saved: {filepath}")
                count += 1

    imap.close()
    imap.logout()
    print(f"\n✅ Downloaded {count} attachments to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Email Tool")
    sub = parser.add_subparsers(dest="cmd")

    # inbox
    ib = sub.add_parser("inbox")
    ib.add_argument("--limit", "-n", type=int, default=10)

    # search
    sr = sub.add_parser("search")
    sr.add_argument("--from", dest="from_addr", default=None)
    sr.add_argument("--subject", default=None)
    sr.add_argument("--days", type=int, default=7)

    # read
    rd = sub.add_parser("read")
    rd.add_argument("--id", required=True)

    # send
    sd = sub.add_parser("send")
    sd.add_argument("--to", required=True)
    sd.add_argument("--subject", "-s", required=True)
    sd.add_argument("--body", "-b", required=True)
    sd.add_argument("--attach", "-a", default=None)
    sd.add_argument("--html", action="store_true")

    # download-attachments
    da = sub.add_parser("download-attachments")
    da.add_argument("--id", required=True)
    da.add_argument("--output-dir", "-o", default=os.path.join(DEFAULT_OUTPUT_DIR, "attachments"))

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    if args.cmd == "inbox":
        inbox(args.limit)
    elif args.cmd == "search":
        search_emails(args.from_addr, args.subject, args.days)
    elif args.cmd == "read":
        read_email(args.id)
    elif args.cmd == "send":
        send_email(args.to, args.subject, args.body, args.attach, args.html)
    elif args.cmd == "download-attachments":
        download_attachments(args.id, args.output_dir)


if __name__ == "__main__":
    main()
