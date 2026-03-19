---
name: secret-manager
description: Manage API keys securely via system keyring (macOS Keychain / GNOME Keyring) and inject them into OpenClaw config.
triggers: 
homepage: https://github.com/openclaw/skills
metadata: {"clawdbot":{"emoji":"🔐","requires":{"anyBins":["security","secret-tool"]},"install":[{"id":"bash","kind":"bash","bin":"secret-manager.sh","label":"Install Secret Manager (bash)"}]}}
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["secret-management", "api-keys", "security"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🔐", "category": "tools", "priority": "medium"}
---

# Secret Manager

A secure way to manage API keys for OpenClaw using the system keyring.

- **macOS**: Uses Keychain Access via `security` command
- **Linux**: Uses GNOME Keyring via `secret-tool` (libsecret)

This skill provides a `secret-manager` CLI that:
1.  Stores API keys securely in the OS keyring.
2.  Injects them into your `auth-profiles.json`.
3.  (Linux only) Propagates them to `systemd` user environment.
4.  (Linux only) Restarts the OpenClaw Gateway service inside your Distrobox container.

## Installation

### macOS (no extra dependencies)
macOS Keychain is built-in. No installation needed.

### Linux
Ensure you have the dependencies:
- **Debian/Ubuntu:** `sudo apt install libsecret-tools`
- **Fedora:** `sudo dnf install libsecret`
- **Arch:** `sudo pacman -S libsecret`

Copy the script to your path or run it directly.

## macOS Usage

```bash
# Store a key
security add-generic-password -a "openclaw" -s "OPENAI_API_KEY" -w "sk-xxx" -U

# Retrieve a key
security find-generic-password -a "openclaw" -s "OPENAI_API_KEY" -w

# Delete a key
security delete-generic-password -a "openclaw" -s "OPENAI_API_KEY"

# List all OpenClaw keys
security dump-keychain | grep -A5 "openclaw"
```

## Configuration

The script uses default paths that work for most OpenClaw installations, but you can override them with environment variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `OPENCLAW_CONTAINER` | Name of the Distrobox container (Linux only) | `clawdbot` |
| `OPENCLAW_HOME` | Path to OpenClaw config directory | `~/.openclaw` |
| `SECRETS_ENV_FILE` | Path to an optional .env file to source | `~/.config/openclaw/secrets.env` |
| `KEYRING_BACKEND` | Force backend: `keychain` (macOS) or `libsecret` (Linux) | auto-detect |

## Usage

**List all configured keys:**
```bash
secret-manager list
```

**Set a key (interactive prompt):**
```bash
secret-manager OPENAI_API_KEY
# (Paste key when prompted)
```

**Set a key (direct):**
```bash
secret-manager DISCORD_BOT_TOKEN "my-token-value"
```

**Supported Keys:**
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `DISCORD_BOT_TOKEN`
- `GATEWAY_AUTH_TOKEN`
- `OLLAMA_API_KEY`
- `GIPHY_API_KEY`
- `GOOGLE_PLACES_API_KEY`
- `LINKEDIN_LI_AT`
- `LINKEDIN_JSESSIONID`
