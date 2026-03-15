# Changelog

All notable changes to xyvaClaw will be documented in this file.

## [1.1.0] - 2026-03-15

### Performance
- `bootstrapMaxChars` 5000 → 16000 (better first-turn accuracy)
- Skill preload expanded to 8 high-frequency skills (zero cold-start)
- `responseWatchdogSec` 15 → 30 (reduce API timeout false-positives)
- Session idle timeout 180 → 360 min (complex tasks)
- claw-shell: polling-based output detection replaces fixed 500ms wait

### Security
- claw-shell: expanded dangerous command detection (chmod 777, curl|bash, fork bomb, etc.)

### Bug Fixes
- browser-pilot: removed contradictory docs (AI can now use file upload/multi-tab)
- effect-tracker: fixed hardcoded `~/.openclaw/` path → `$OPENCLAW_HOME`
- miniflux-news: fixed legacy brand name `clawdbot` → `xyvaclaw` (backward compatible)
- TOOLS.md: synced `sessionDispatchConcurrency` and `responseWatchdogSec` with actual config

### New Skills
- **pptx-generator** — Create PowerPoint from JSON or Markdown
- **pdf-processor** — Extract text/tables, merge, split, convert to images
- **voice** — TTS (edge-tts, 200+ voices) + STT (Whisper API / local whisper.cpp)
- **email** — IMAP read/search + SMTP send with attachments

### Install
- Auto-install `python-pptx`, `pdfplumber`, `PyPDF2` (failure never blocks install)

### Repo
- Added `CONTRIBUTING.md`, `SECURITY.md`
- Added GitHub Issue templates (bug report, feature request)
- Added Pull Request template
- Added GitHub Actions CI for auto-release on tag push
- Existing Claw detection in installer (detect OpenClaw/QClaw/AutoClaw/WorkBuddy/CoPaw)
- `website/` removed from repo (lives in separate XyvaClaw-web repo)

## [1.0.0] - 2026-03-12

### Initial Release
- 38 pre-installed skills
- 5-level model fallback (DeepSeek → Qwen → Kimi → DeepSeek Reasoner → Qwen Max)
- Lossless context engine (DAG-based summarization)
- 4-tier memory system (session → daily → long-term → knowledge graph)
- Deep Feishu/Lark integration (112 TypeScript source files)
- Self-evolution engine (error learning + effect tracking + proactive reflection)
- One-click installer with Web Setup Wizard
- macOS + Linux support
