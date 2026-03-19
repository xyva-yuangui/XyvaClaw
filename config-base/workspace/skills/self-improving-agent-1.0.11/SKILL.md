---
name: self-improvement
description: Captures learnings, errors, corrections for continuous improvement.
triggers: 
version: 1.0.0
status: stable
updated: 2026-03-11
provides: ["self_improvement"]
os: ["darwin", "linux", "win32"]
clawdbot: {"emoji": "🛠️", "category": "tools", "priority": "medium"}
---

# Self-Improvement Skill

## Quick Reference
| Situation | Action |
|-----------|--------|
| Command fails | Log to `.learnings/ERRORS.md` |
| User corrects you | `.learnings/LEARNINGS.md` (correction) |
| Missing feature | `.learnings/FEATURE_REQUESTS.md` |
| Better approach found | `.learnings/LEARNINGS.md` (best_practice) |
| Broadly applicable | Promote to AGENTS.md / TOOLS.md / SOUL.md |

## Trigger
Auto: on failure, correction, or feature request.

> Full reference: `SKILL-REFERENCE.md`
