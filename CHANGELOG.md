# Changelog

All notable changes to xyvaClaw will be documented in this file.

## [1.1.5] - 2026-03-19

### Breaking Changes
- **Gateway auth mode**: Local mode (`bind: loopback`) now defaults to `auth.mode: none`. Users no longer need to enter a gateway token to access Dashboard. Non-loopback mode still uses token auth.

### New Features
- **API Key smart input**: Interactive terminal prompt during install — auto-detects key type (`sk-sp-` → Bailian Coding Plan, `sk-` → Bailian Standard / DeepSeek) and validates via HTTP request.
- **Zero-confirmation install**: Removed all y/n prompts (sudo wrapper, auto-start, gateway launch). Install completes fully automatically after entering API Key.
- **Auto-start gateway**: Gateway starts automatically after install and opens browser to Dashboard.

### Bug Fixes
- **Gateway won't start — `plugins.allow: plugin not found`**: `openclaw plugins install --link` was silently failing (stderr suppressed). Added error output + fallback manual `load.paths` injection.
- **Gateway won't start — `channels.webchat: unknown channel id`**: OpenClaw doctor injects `webchat` channel, but it wasn't in the known channels whitelist. Added `webchat` to `KNOWN_CHANNELS`.
- **Feishu group messages silently dropped**: `groupPolicy` was `allowlist` with empty `allowFrom`. Fixed to `open` with `allowFrom: ["*"]`.
- **Feishu placeholder config leaks**: When no Feishu credentials are provided, the feishu channel is now completely removed from config instead of being disabled with `__APP_ID__` placeholders.

### Changed
- `config-base/openclaw.json.template`: `auth.mode` changed from `token` to `none`
- `installer/restore-config.py`: loopback → `auth: none`; no feishu creds → remove channel entirely
- `xyvaclaw-setup.sh`: replaced Web wizard / manual .env choice with direct API Key prompt; added plugin registration fallback; removed all confirmation prompts

## [1.1.4] - 2026-03-19

### Bug Fixes
- **`__API_KEY__` placeholder overrides real API key**: Agent-level `models.json` files contained `__API_KEY__` placeholders for `bailian` and `deepseek` providers, which overwrote the real key from global `openclaw.json` during config merge. Removed all agent-level `__API_KEY__` placeholders.
- **Hardcoded tokens in `auth-profiles.json`**: Cleared leaked OAuth tokens for `qwen-portal`, hardcoded key for `minimax-cn`, and `__API_KEY__` placeholders for `deepseek`/`bailian`.
- **Bailian baseUrl wrong for Coding Plan keys**: `sk-sp-` keys require `coding.dashscope.aliyuncs.com` but config had `compatible-mode`. Added auto-detection in `restore-config.py` and `setup-wizard/server/index.js`.
- **Setup script doesn't clean placeholders**: Added post-rsync cleanup step to remove `__API_KEY__` placeholders from deployed agent configs.

### Changed
- `config-base/agents/main/agent/models.json`: removed `apiKey` fields from `bailian` and `deepseek`
- `config-base/agents/main/agent/auth-profiles.json`: cleared all hardcoded credentials
- `config-base/agents/quant-analyst/agent/models.json`: removed `apiKey` field from `bailian`
- `installer/restore-config.py`: added `detect_bailian_base_url()` helper
- `setup-wizard/server/index.js`: added dynamic baseUrl detection in validation endpoint
- `xyvaclaw-setup.sh`: added placeholder cleanup step after config deployment

## [1.1.3] - 2026-03-19

### Bug Fixes
- **Feishu WebSocket connected but no messages received**: Confirmed root cause was missing event subscription (`im.message.receive_v1`) on Feishu Open Platform. Documented the required 5-step configuration.
- **Feishu `accounts.main` → `accounts.default`**: OpenClaw expects `accounts.default` but template used `accounts.main`. Fixed template and `restore-config.py`.
- **Feishu DM policy too restrictive**: Changed `dmPolicy` from `allowlist` to `open` and set `allowFrom: ["*"]`.
- **Webchat channel validation error**: `channels.webchat` is not a recognized channel ID in OpenClaw. Added filtering in the plugin registration restore step.
- **Vite build failure in setup wizard**: Fixed missing dev dependencies detection and rebuild trigger.

### Documentation
- `docs/FULL-AUDIT.md`: comprehensive audit report covering all fixes, Feishu debugging, and DingTalk integration plan

## [1.1.2] - 2026-03-19

### Bug Fixes
- **Wizard frontend not rebuilt after code update**: The built `dist/` from v1.1.0 was still being served, missing all v1.1.1 model ID input and auto-detect features. Rebuilt wizard frontend now includes custom provider model configuration UI.
- **Setup script skips rebuild on source changes**: `xyvaclaw-setup.sh` now detects when `src/` files are newer than `dist/index.html` and triggers automatic rebuild, ensuring `git pull` updates are reflected in the wizard UI.
- **Template file fallback**: `restore-config.py` now falls back to the repo's `config-base/openclaw.json.template` if the deployed template is missing, preventing config generation failures on re-runs.

### Changed
- `setup-wizard/dist/`: rebuilt with v1.1.1 custom provider model detection features
- `xyvaclaw-setup.sh`: added source change detection for wizard frontend auto-rebuild
- `installer/restore-config.py`: added fallback template path resolution

## [1.1.1] - 2026-03-16

### Bug Fixes
- **Gateway "Missing config" on startup**: OpenClaw 2026.3.13 reads config from `$OPENCLAW_HOME/.openclaw/openclaw.json` (nested path). `restore-config.py` now outputs to the correct `.openclaw/` directory. Fixed `meta` section (removed unrecognized keys `brand`/`version`/`basedOn`), added required `wizard` section, and stripped stale `plugins` entries for fresh installs.
- **Custom Provider models not showing**: Setup Wizard now collects model IDs when adding a custom provider — via manual input or auto-detect (`🔍 检测模型` button calls `/api/detect-models` on OpenAI-compatible `/models` endpoint). Models are persisted through `.env` (`CUSTOM_PROVIDER_{i}_MODELS`) and correctly written into `openclaw.json`.
- **Feishu appSecret SecretRef error**: Changed `channels.feishu.appSecret` from SecretRef object `{source:"env", id:"..."}` to plain string — SecretRef requires runtime gateway snapshot resolution which fails on fresh installs.

### Changed
- `config-base/openclaw.json.template`: fixed `meta` format and `appSecret` to plain placeholder
- `installer/restore-config.py`: outputs to `.openclaw/openclaw.json`, supports `--output-dir`, adds `wizard` section, strips plugins, reads custom providers from `.env`
- `setup-wizard/src/pages/ModelKeys.jsx`: added model ID textarea, auto-detect button, model tags on provider cards, empty-models warning
- `setup-wizard/server/index.js`: added `POST /api/detect-models` endpoint, custom provider env vars in `save-config`
- `xyvaclaw-setup.sh`: updated config output path references

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
