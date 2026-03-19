#!/usr/bin/env python3
"""Dependency check for email skill."""
import sys, os

def check():
    ok = True
    # All deps are stdlib
    try:
        import imaplib, smtplib, email
        print("✅ imaplib + smtplib + email (stdlib)")
    except ImportError:
        print("❌ Standard library modules missing (unexpected)")
        ok = False

    # Check config
    env_file = os.path.join(
        os.environ.get("OPENCLAW_HOME", os.path.expanduser("~/.xyvaclaw")),
        ".env"
    )
    has_config = False
    if os.path.exists(env_file):
        with open(env_file) as f:
            content = f.read()
        if "EMAIL_IMAP_HOST" in content and "EMAIL_USER" in content:
            has_config = True

    if has_config:
        print("✅ Email config found in .env")
    else:
        print("⚠️ Email not configured. Add EMAIL_IMAP_HOST, EMAIL_USER, EMAIL_PASSWORD to .env")

    return ok

if __name__ == "__main__":
    sys.exit(0 if check() else 1)
