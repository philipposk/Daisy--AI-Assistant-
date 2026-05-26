# Daisy Assistant — Changelog

## 1.5 — Stable Release (2026-05-26)

**Packaging & deployment**
- `tools/launchd_setup.py` — install/uninstall/status for macOS launchd auto-start
  - Writes `~/Library/LaunchAgents/com.daisy.assistant.plist`
  - `KeepAlive = true` with 10 s throttle; logs to `~/.daisy/logs/`
- `setup.sh` updated for first-run: creates config dirs, checks Python deps
- `GET /api/health` — lightweight health check for uptime monitors
- `GET /api/version-history` — full release history via API
- `CHANGELOG.md` (this file) polished

---

## 1.4 (2026-05-26)

**Undo stack**
- `services/undo_stack.py`: `UndoStack` (LIFO, cap 50) + `UndoManager`
- Reverses: `create_note` (delete file), `create_task` (remove line from tasks.md),
  `create_reminder` (remove from reminders.json), `memory_remember` (forget from DB)
- `DaisyPipeline._push_undo()` called after every successful action

**New API endpoints**
- `GET /api/undo` — list undo stack
- `POST /api/undo` — execute undo of most recent action
- `GET /api/log?lines=N` — tail audit log (JSONL)
- `GET /api/settings` — read current config as flat dict

**Tests**: 189/189 ✅

---

## 1.3 (2026-05-26)

**Long-term memory**
- `services/memory.py`: `MemoryStore` (SQLite `memory.db`) + `ConversationSummarizer`
- `MemoryStore`: `remember / recall / search / forget / list_all`
- `ConversationSummarizer`: compresses old turns when history exceeds `max_turns`
  (extractive fallback; uses LLM if available)
- Pipeline injects top-3 relevant memories into every LLM call

**New API endpoints**
- `GET /api/memory` — list all memories
- `GET /api/memory/search?q=` — keyword search
- `GET /api/memory/{topic}` — recall single memory
- `POST /api/memory` — store / update
- `DELETE /api/memory/{topic}` — forget

**Tests**: 173/173 ✅

---

## 1.2 (2026-05-26)

**macOS native integrations**
- `services/mac_calendar.py`: list/create Calendar events + Reminders via AppleScript
- `services/mac_mail.py`: read/search/send/draft email via Mail.app
- New action types: `CreateCalendarEventAction`, `CreateMacReminderAction`, `SendEmailAction`

**New API endpoints**
- `GET/POST /api/calendar/events` — today's events; create event
- `GET /api/calendar/calendars` — list calendar names
- `GET/POST /api/mac-reminders` — list/create Reminders
- `GET /api/mail/messages`, `GET /api/mail/search`, `POST /api/mail/send`

**Tests**: 152/152 ✅

---

## 1.1 (2026-05-26)

**macOS Keychain**
- `services/keychain.py`: wrapper around macOS `security` CLI — no pip deps
- Config loader gains Keychain overlay (between file config and env vars)
- Known keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`

**New API endpoints**
- `GET /api/keychain` — list known keys + which are set
- `POST /api/keychain` — store key in Keychain
- `DELETE /api/keychain/{name}` — remove key from Keychain

**Tests**: 125/125 ✅

---

## 1.0 (2026-05-26)

**Frontend streaming**
- SSE endpoint `GET /api/turn-stream?text=` — typewriter effect via `EventSource`
- Events: `transcript` → `partial` (×N) → `done`

**macOS permissions**
- `services/permissions.py`: check mic (PyAudio probe), accessibility (osascript),
  screen recording (Quartz `CGPreflightScreenCaptureAccess`)
- `GET /api/permissions` — current grant status
- `GET /api/permissions/open?kind=` — open System Settings pane

**Menu-bar app**
- `daisy_menubar.py`: rumps tray icon; polls `/api/state` every 3 s; Status/Open/Quit menu

**Tests**: 117/117 ✅

---

## 0.9 (2026-05-25)

**Modern OSS voice stack**
- `RealtimeSTT` integration (WebRTC + Silero VAD + faster-whisper)
- `Kokoro-ONNX` TTS (Apache-2.0); Piper fallback
- openWakeWord backend for "daisy" wake word

**Daisy as MCP server**
- `daisy_mcp_server/server.py` — exposes `listen`, `speak`, `notify`, `confirm` tools
- Claude Code and any MCP client can use Daisy as voice front-end

**Other**
- `services/transcript_filter.py` — drop Whisper hallucination phantoms
- `services/tool_router.py` — keyword MCP tool router (sentence-transformers optional)
- `daisy_server/` — FastAPI backend; `frontend/Daisy.html`; `daisy_app.py` (PyWebView)

---

## 0.8 (2026-05-25)

- Wake-word loop (`services/wake_word.py`)
- Barge-in during TTS (`services/barge_in.py`)
- Confirmation prompts that actually block (`services/confirmation.py`)
- Reminder scheduler (background thread, osascript notifications, TTS)
- MCP desktop automation (`mcp-desktop-automation/server.js`, 12 tools)
- Computer-use fallback (`mcp-computer-use/server.py`)
- Anthropic Claude provider; date injection; conversation summary compression
- Fallback provider chain with exponential back-off

---

## 0.7 (2026-05-25)

Bug-fix release (22 fixes):
- Deduplicated shebang / import block in `daisy.py`
- TTS uses correct API key; `tempfile.NamedTemporaryFile` instead of deprecated `mktemp`
- Piper TTS implemented (shell-out); system TTS voice from config
- Groq model respects `config.llm.model`
- JSON extractor handles nested objects / arrays
- Note filename collision prevention (timestamp suffix)
- Single shared `PersistenceLayer` (removed duplicate DB schema)
- Safety checker uses `shlex` tokenisation (no more substring false-positives)
- Dead YAML import branch removed; env-var overlay includes `ANTHROPIC_API_KEY`

---

## 0.6 (initial open-source release)

Clean rewrite of the original monolith:
- Service architecture: `VoiceService`, `BrainService`, `ActionService`, `SafetyChecker`
- Pydantic v2 typed schemas throughout
- SQLite persistence for tasks + conversation memory
- Audit log (JSONL append-only)
- YAML/JSON config with env-var overrides
- 41 unit tests
