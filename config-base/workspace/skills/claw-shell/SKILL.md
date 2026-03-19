---
name: claw-shell
description: |
triggers: 
metadata: 
openclaw: 
emoji: "🐚"
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["claw_shell"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# claw-shell

ALWAYS USES TMUX SESSION `claw`.

## PURPOSE

- RUN SHELL COMMANDS INSIDE TMUX SESSION `claw`
- NEVER TOUCH ANY OTHER SESSION
- READ OUTPUT BACK TO THE AGENT

## INTERFACE

### Tool: `claw_shell_run`

**Inputs:**

- `command` (string, required): shell command to run inside session `claw`.

**Behavior:**

1. Attach to tmux session `claw` (create it if missing: `tmux new -s claw -d`).
2. Send the command followed by Enter.
3. Capture the latest pane output.
4. Return the captured output to the agent.

## SAFETY

- DO NOT RUN:
  - `sudo`
  - `rm` (without explicit user approval)
  - `reboot`, `shutdown`, or destructive system-level commands
- IF THE COMMAND CONTAINS ANY OF THE ABOVE:
  - ASK USER FOR CONFIRMATION BEFORE EXECUTING.

## EXAMPLES

- SAFE:
  - `ls -la`
  - `bird read https://x.com/...`
  - `git status`

- DANGEROUS (ASK FIRST):
  - `rm -rf ...`
  - `docker system prune -a`
  - `chmod -R ...`