# Daisy Assistant — Changelog

Each release starts with a summary of what changed for the user, followed by technical details.

---

## 1.6 — Hardening release (2026-06-01)

**What this gives you:**
Daisy got a full security and reliability audit, and everything found got fixed.
The biggest changes you'll feel: "undo" now survives restarts, the app window
finally shows YOUR real conversation and tasks (not demo content), there's a real
settings screen (API keys, voice, provider — no terminal needed), and the
confirmation prompts for risky actions now actually fire every time. Under the
hood she's much harder to trick: quotes in calendar titles or emails can't break
out into script execution anymore, and random websites can't poke her local API.

**Technical details:**
- **Confirmation layer enforced**: per-action confirmation can no longer be
  bypassed by the LLM's intent flag (`daisy.py` no longer derives `auto_approve`
  from `intent.requires_confirmation`); the flag can only ADD confirmation.
  Auto-approval is an explicit per-request API opt-in, audit-logged, with no
  shared-state mutation (the old provider-swap race is gone).
- **AppleScript injection closed**: shared `_escape()` (backslash-first) in
  `mac_calendar.py`, `mac_mail.py` (incl. to/cc), `daisy_mcp_server`,
  `mcp-desktop-automation/server.js` (now `execFile`, no shell); locale-safe
  numeric AppleScript dates; 30s osascript timeouts.
- **Cross-origin guard**: middleware rejects browser requests with a foreign
  Origin header; `auto_approve` removed from the GET /api/turn-stream interface.
- **Persistent undo**: stack survives restarts (`~/.daisy/undo.json`, atomic
  writes); note-undo uses the exact written path from `ActionResult.metadata`;
  reminder-undo deletes only the one created reminder (created_at match).
- **Thread safety**: turns serialized with a pipeline lock; `reminders.json`
  guarded by a shared lock + atomic replace (`services/reminders_store.py`);
  SQLite uses one WAL connection behind a lock instead of per-call connects.
- **Safety checker hardened**: blocks nested shells (`bash -c …`), command
  substitution (`$(…)`, backticks), and structural `rm -rf` variants
  (`-fr`, `--recursive --force`, `-Rf`).
- **Brain parser completed**: `mcp_tool_call`, `create_calendar_event`,
  `create_mac_reminder`, `send_email` now parse from LLM output (previously
  silently dropped); JSON-parse total failure no longer reads raw provider
  errors aloud.
- **MCP plumbing**: real read timeouts, stderr drain thread, `atexit` cleanup
  of child servers; computer-use kills the whole process group on timeout.
- **App shell**: default port unified to 5188; uvicorn shuts down gracefully on
  window close; menubar polls via `rumps.Timer` (main thread); launchd uses
  `bootstrap`/`bootout` with `KeepAlive SuccessfulExit=false`.
- **Frontend rebuilt**: demo placeholder content removed; real tasks sidebar,
  undo button, settings panel (Keychain keys, provider/voice, PATCH
  /api/settings), memory viewer, audit-log viewer, SSE auto-retry + offline
  banner, aria-live + contrast fixes.
- **New — provider circuit breaker + cost tracking** (`services/provider_health.py`,
  ported from the AI-OS project): a provider that fails 3× in a row is skipped
  for a 2-minute cooldown instead of timing out every turn; a rough running
  spend estimate per provider persists to `~/.daisy/costs.json`. Exposed at
  `GET /api/providers/health` and `GET /api/costs`.
- **New — free-tier LLM rotation**: set `llm.provider: free` to route through
  `llm-free-rotator` (Groq / OpenRouter / NVIDIA) for $0 operation.
- **New — portable memory**: `GET /api/memory/export` (SecondBrain markdown +
  YAML frontmatter) and `POST /api/memory/import`.
- **New — writable settings**: `PATCH /api/settings` persists provider, model,
  voice and toggles to `~/.daisy/config.yaml`.
- **Pydantic v2 clean**: `model_dump(mode="json")`, `ConfigDict` — zero
  deprecation warnings.
- Stale 0.6-era docs rewritten (QUICKSTART, START_DAISY); dead
  `START_INTERACTIVE.sh` removed.

---

## 1.5 — Stable release (2026-05-26)

**What this gives you:**
Daisy can now start automatically when you log in to your Mac. One command sets it
up; she'll run quietly in the background, restart herself if she crashes, and stay
out of your way. The setup script is cleaner, there's a proper changelog file (this
one), and the API has a "are you alive?" check so other tools can watch Daisy.

**Technical details:**
- `tools/launchd_setup.py` — `install` / `uninstall` / `status` commands
- Writes `~/Library/LaunchAgents/com.daisy.assistant.plist`, `KeepAlive=true`, 10s throttle, logs to `~/.daisy/logs/`
- `setup.sh` rewritten — Python version check, Keychain hints, permissions snapshot, default-config writer
- `GET /api/health` — `{"status":"ok","version":"1.5","ts":...}`
- `GET /api/version-history` — full 0.5 → 1.5 list
- 9 new tests (launchd plist generator + health/version endpoints)
- **198/198 tests passing**

---

## 1.4 (2026-05-26)

**What this gives you:**
You can now say "undo" and Daisy actually undoes the last thing she did — deletes
the note, removes the task, cancels the reminder, or forgets the fact you just told
her. You can also see a log of everything she's done recently, and ask her current
settings (which voice, which AI provider, etc).

**Technical details:**
- `services/undo_stack.py` — LIFO `UndoStack` (cap 50) + `UndoManager`
- Reverses: `create_note` (delete file), `create_task` (remove line from tasks.md), `create_reminder` (remove from reminders.json), `memory_remember` (forget topic)
- `DaisyPipeline._push_undo()` called after every successful action result
- `GET /api/undo` (list), `POST /api/undo` (execute), `GET /api/log?lines=N`, `GET /api/settings`
- 16 new tests
- **189/189 tests passing**

---

## 1.3 (2026-05-26)

**What this gives you:**
Daisy now remembers things across conversations. Tell her once "I prefer Python",
"my dog's name is Rex", or "I work at Acme Corp", and she'll still know next week.
She also automatically summarizes long conversations so she doesn't lose track of
context (or rack up huge token bills) when you've been chatting for hours.

**Technical details:**
- `services/memory.py` — SQLite-backed `MemoryStore` + `ConversationSummarizer`
- `MemoryStore`: `remember / recall / search / forget / list_all` (keyword scoring, no embeddings)
- `ConversationSummarizer`: extractive fallback; optional LLM summary if brain service supports it
- Pipeline injects top-3 relevant memories into every brain call
- API: `GET /api/memory`, `GET /api/memory/search?q=`, `GET /api/memory/{topic}`, `POST /api/memory`, `DELETE /api/memory/{topic}`
- 21 new tests
- **173/173 tests passing**

---

## 1.2 (2026-05-26)

**What this gives you:**
Daisy can now read and write to your Mac's Calendar, Reminders, and Mail apps. Ask
her what's on your schedule today, have her book a dentist appointment, list your
to-dos, add new reminders, check recent emails, search your inbox, or draft/send
an email — all by voice.

**Technical details:**
- `services/mac_calendar.py` — list/create Calendar events + Reminders via AppleScript (`osascript`)
- `services/mac_mail.py` — read/search/send/draft email via Mail.app
- New action types: `CreateCalendarEventAction`, `CreateMacReminderAction`, `SendEmailAction`
- API: `/api/calendar/events` (GET/POST), `/api/calendar/calendars`, `/api/mac-reminders` (GET/POST), `/api/mail/messages`, `/api/mail/search`, `/api/mail/send`
- AppleScript output parser hardened against trailing-separator artifacts
- 27 new tests
- **152/152 tests passing**

---

## 1.1 (2026-05-26)

**What this gives you:**
Your API keys (OpenAI, Anthropic, etc.) no longer sit in plain-text config files.
They go in the macOS Keychain — the same secure storage your Mac uses for WiFi
passwords. You manage them from the UI or via API; deleting a key wipes it from
the Keychain.

**Technical details:**
- `services/keychain.py` — wrapper around macOS `security` CLI, zero pip dependencies
- Known keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`
- Config loader overlay order: defaults → file → **Keychain** → env vars
- API: `GET /api/keychain` (list), `POST /api/keychain` (store), `DELETE /api/keychain/{name}`
- 8 new tests (mocked `subprocess.run`)
- **125/125 tests passing**

---

## 1.0 (2026-05-26)

**What this gives you:**
Daisy now feels like a real Mac app instead of a script. There's a small icon in
your menu bar that shows whether she's listening, speaking, or idle. Her replies
type out word-by-word like a chat app instead of arriving in one chunk. And when
she needs microphone or screen-recording permission, she walks you straight to the
right pane in System Settings instead of leaving you to find it.

**Technical details:**
- SSE endpoint `GET /api/turn-stream?text=` — `EventSource`-friendly, events: `transcript` → `partial`×N → `done`
- `services/permissions.py` — checks Mic (PyAudio probe), Accessibility (osascript), Screen Recording (Quartz `CGPreflightScreenCaptureAccess`)
- `GET /api/permissions`, `GET /api/permissions/open?kind=mic|accessibility|screen` (deep-links System Settings)
- `daisy_menubar.py` — rumps tray icon, polls `/api/state` every 3s, Status / Open / Permissions / Quit menu
- **117/117 tests passing**

---

## 0.9 (2026-05-25)

**What this gives you:**
Daisy gets a real web UI (no command-line needed), can listen with better quality
voice models that run locally on your Mac, and can be used as a voice front-end by
other AI tools (like Claude Code). She also stops hallucinating words from background
noise.

**Technical details:**
- `RealtimeSTT` integration (WebRTC + Silero VAD + faster-whisper); streaming partials
- `Kokoro-ONNX` TTS (Apache-2.0, 82M params, local CPU); Piper fallback
- openWakeWord backend for "daisy" wake word (custom-trained model recommended)
- `daisy_mcp_server/server.py` — Daisy IS an MCP server (`listen`, `speak`, `notify`, `confirm` tools)
- `services/transcript_filter.py` — drops Whisper hallucination phantoms ("thanks for watching", "subtitles by…")
- `services/tool_router.py` — keyword-based MCP tool router (sentence-transformers optional for embeddings)
- `daisy_server/` — FastAPI backend
- `frontend/Daisy.html` — single-file SPA, wired via `fetch` + `EventSource` + WebSocket
- `daisy_app.py` — PyWebView native shell

---

## 0.8 (2026-05-25)

**What this gives you:**
Daisy becomes a real voice assistant instead of a "press button, then talk" tool.
She listens continuously for her name, lets you cut her off when she's talking too
much, actually asks before doing risky things, and fires reminders on time. She
can also drive other apps on your desktop (open Xcode, click buttons, take
screenshots) and talk to Anthropic's Claude models, not just OpenAI.

**Technical details:**
- `services/wake_word.py` — openWakeWord or Whisper-poll backend
- `services/barge_in.py` — VAD listener during TTS, terminates playback handle on speech detection
- `services/confirmation.py` — `CLIConfirmationProvider`, `VoiceConfirmationProvider`, auto-approve/reject
- `services/reminder_scheduler.py` — background thread, polls `reminders.json`, fires via `osascript display notification` + TTS
- `mcp-desktop-automation/server.js` (Node, 12 tools: `take_screenshot`, `build_with_retry`, etc.)
- `mcp-computer-use/server.py` — Agent-S wrapper as last-resort GUI driver
- Anthropic provider in `brain_service.py` with prompt-caching support
- Date injection into system prompt; conversation history summarization
- Fallback provider chain with exponential back-off

---

## 0.7 (2026-05-25)

**What this gives you:**
A maintenance release — Daisy got noisier and more reliable. Voice replies stopped
being silent on launch, her TTS started using the right voice from your config,
the safety filter stopped incorrectly blocking harmless commands, and a dozen
other rough edges got sanded down. No new features, just everything working as
intended.

**Technical details (22 fixes):**
- Deduped shebang/import block in `daisy.py`
- Startup greeting now actually plays
- TTS uses dedicated API key; `tempfile.NamedTemporaryFile` instead of deprecated `mktemp`
- Piper TTS implemented (shell-out to `piper` binary); system TTS voice from config
- Groq model respects `config.llm.model`
- JSON extractor handles nested objects / arrays
- Note filename collision prevention (`_2`, `_3` suffix)
- Single shared `PersistenceLayer` (removed parallel DB schema in `ActionService`)
- Safety check runs once (dispatcher only); confirmation-required actions return failed `ActionResult` with reason
- Safety checker uses `shlex` tokenisation (no more "curl" matching "currently", "su" matching "sudo")
- Whitelist matches `basename(token[0])` — `/usr/bin/ls` works
- Dead YAML import branch removed
- Env-var overlay includes `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`
- `afplay` runs via `Popen` so playback handle is killable for barge-in
- Safety test rewritten for shlex semantics
- **41/41 tests passing**

---

## 0.6 (initial open-source release, 2026-05-24)

**What this gives you:**
The first version of Daisy with a proper structure. Instead of one giant Python
file, she has clean separate modules for listening, thinking, and doing things.
She remembers conversations across sessions in a small database, logs everything
she does, and has guardrails against running anything destructive.

**Technical details:**
- Service architecture: `VoiceService`, `BrainService`, `ActionService`, `SafetyChecker`
- Pydantic v2 typed schemas (`TranscriptionResult`, `AssistantIntent`, `AssistantAction`, `ActionResult`)
- Action types: `CreateNote`, `CreateTask`, `CreateReminder`, `RunCommand`, `Conversation`
- SQLite persistence (tasks + conversation memory)
- JSONL audit log (append-only)
- YAML/JSON config with env-var overrides
- 41 unit tests

---

## 0.5 (predecessor, 2025)

**What this gave you:**
The first working version of Daisy — voice-first, monolithic, but actually useful.
She had wake-word listening, could control other apps on your desktop, and even
had a sub-tool called "Praiser" for tracking compliments. Rough around the edges,
but the proof that the idea worked.

**Technical details:**
- Voice-first loop with wake word
- MCP desktop automation server (12 tools)
- Intelligent build-retry for Xcode/Android projects
- Praiser sub-app
- Free-form LLM responses (no typed schemas yet)
- Monolithic `daisy-assistant.py`
