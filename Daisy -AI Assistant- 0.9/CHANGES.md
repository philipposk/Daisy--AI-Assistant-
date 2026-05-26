# Daisy 0.9 — OSS Stack + Frontend Release

0.9 finishes the picture: modern open-source voice stack, Daisy exposed as
its own MCP server, and a real desktop UI (the user's Cursor-style HTML
mockup wired up to a FastAPI backend with a native-window launcher).

## What's new

### 1. Frontend (`frontend/Daisy.html` + `daisy_server/app.py` + `daisy_app.py`)
The big one. `frontend/Daisy.html` is the polished Cursor-style proto from the
user's Daisy.zip, now wired to a FastAPI backend:
- Sidebar new-task input is the composer; Enter sends a turn.
- Mic button calls `/api/listen` → mic capture → STT → turn.
- Topbar pulse shows the active provider chain in its tooltip; version
  badge auto-updates from `/api/state`.
- ⌘K focuses the composer.
- Transcript panel materializes inline under the main pane so user +
  Daisy bubbles are visible.

`daisy_server/app.py` — FastAPI app:
- `GET  /`                      → serves `frontend/Daisy.html`
- `GET  /api/state`             → version, provider chain, feature flags
- `POST /api/turn`              → run a single text turn
- `POST /api/listen`            → mic → STT → turn
- `GET  /api/tasks`             → tasks from the shared PersistenceLayer
- `POST /api/tasks/{id}/done`   → complete task
- `GET  /api/reminders`         → read reminders.json
- `WS   /api/stream`            → JSON-over-websocket for live UIs

`daisy_app.py` — single-file launcher:
- Starts uvicorn in a background thread.
- Opens a native window via `pywebview` if available; falls back to the
  system browser otherwise. `--no-ui` flag for headless mode.

### 2. RealtimeSTT path (`services/voice_service.py::_transcribe_realtimestt`)
- New `stt.provider: "realtimestt"` option backed by `faster-whisper`.
- `stt.local_model` config field (default `base.en`).
- Optional dep: `pip install faster-whisper`. Falls back gracefully.

### 3. Kokoro TTS (`services/voice_service.py::_tts_kokoro`)
- New `tts.provider: "kokoro"` option. Apache-2.0 model + weights.
- Config: `tts.kokoro_model`, `tts.kokoro_voices`, `tts.kokoro_voice`.
- Optional dep: `pip install kokoro-onnx soundfile`.

### 4. Whisper hallucination filter (`services/transcript_filter.py`)
- Drops phantom strings whisper-family models invent on silence
  ("thanks for watching", bare "you", `[music]`, etc.).
- Wraps every `VoiceService.transcribe_audio_file` result transparently.

### 5. Daisy-as-MCP-server (`daisy_mcp_server/server.py`)
Other agents (Claude Code, OpenAI Agents SDK, Pipecat) can call Daisy's
mic + speaker as MCP tools:
- `listen(timeout_seconds=10)`     → transcribed text
- `speak(text)`                    → "ok"
- `notify(message, voice=True)`    → desktop notification + optional TTS
- `confirm(prompt)`                → "yes" | "no" via voice

JSON-RPC over stdio.

### 6. MCP tool router (`services/tool_router.py`)
- `EmbeddingRouter` — sentence-transformers `all-MiniLM-L6-v2`; local; free.
- `KeywordRouter` — cheap fallback using token overlap. Always works.
- `build_tool_router()` factory auto-picks the best available.

## New tests
- `tests/test_transcript_filter.py`
- `tests/test_tool_router.py`
- `tests/test_server.py`
- `tests/test_daisy_mcp_server.py`

## Config surface (new)

```yaml
stt:
  provider: "realtimestt"
  local_model: "base.en"
tts:
  provider: "kokoro"
  kokoro_model: "~/.daisy/kokoro/kokoro-v1.0.onnx"
  kokoro_voices: "~/.daisy/kokoro/voices-v1.0.bin"
  kokoro_voice: "af_sarah"
```

## Optional deps

None required — Daisy 0.9 still runs on a fresh machine:
- `pip install fastapi uvicorn`             → web backend (UI)
- `pip install pywebview`                   → native window
- `pip install faster-whisper`              → local STT
- `pip install kokoro-onnx soundfile`       → local neural TTS
- `pip install sentence-transformers`       → embedding-based tool router
- `pip install openwakeword pyaudio webrtcvad` → wake word + barge-in

## Limitations / what's left for 1.0

- Streaming partials over the WS aren't piped yet (hook exists; STT side
  needs to emit them).
- No menu-bar tray icon yet (window-only).
- No first-run permission-grant flow (mic + accessibility).
- Cross-platform: macOS-only, same as 0.8.

---

# Daisy 0.8 — Logic-Complete Release

0.8 fills in the half-implemented pieces 0.6 documented but didn't ship, and
re-adds what 0.5 had but 0.6 dropped (voice-first loop pieces, MCP desktop
automation, confirmation prompts that actually block, working reminders). No
new frontend yet — that lands with 0.9.

## What's new

### 1. Wake-word loop (`services/wake_word.py`, `WakeWordConfig`)
Two pluggable backends:
- **openWakeWord** — pip package + a custom `daisy.onnx` model. Offline, low CPU.
- **Whisper poll** — fallback that records 1.5s chunks and runs them through STT,
  looking for the wake word. Works with no extra dependency (uses the existing
  `VoiceService`).
- Factory `build_wake_word_backend()` picks the right one and gracefully
  downgrades if openWakeWord isn't installed or no model is configured.
- Disabled by default (`wake_word.enabled: false`) so 0.8 stays drop-in.

### 2. Barge-in (`services/barge_in.py`)
Background VAD listener that interrupts TTS playback as soon as the user
starts talking. Uses WebRTC VAD if available; energy-threshold fallback
otherwise. Hooks into the `Popen` handle 0.7 introduced (`VoiceService.stop_playback`).
Use via `speak_with_barge_in(voice_service, text)`.

### 3. Confirmation prompts that actually block
- New `services/confirmation.py` with four providers:
  - `CLIConfirmation` — y/N on stdin.
  - `VoiceConfirmation` — TTS asks, STT parses yes/no.
  - `AutoApproveConfirmation` / `AutoRejectConfirmation` for tests + headless.
- Dispatcher rewired: when an action requires confirmation, it now calls the
  provider. Approval → execute. Decline → returns `ActionResult(success=False,
  error="Declined by user")`. Replaces 0.7's "rejected with explanation"
  placeholder.
- `confirmation.mode` config selects the backend (default `cli`).

### 4. Reminder scheduler that actually fires
- New `services/reminder_scheduler.py`. Background thread polls
  `reminders.json` every `reminder.poll_seconds` (default 30).
- Fires past-due reminders via macOS `osascript display notification` +
  optional TTS through the supplied `VoiceService`.
- Recurring reminders re-scheduled by `recurring_interval` (default 24h).
- Started by `DaisyPipeline.__init__` when `reminder.enabled` (default true).

### 5. MCP desktop automation (back from 0.5)
- `mcp-desktop-automation/server.js` lifted verbatim from 0.5 — 12 tools
  (`take_screenshot`, `click_mouse`, `type_text`, `key_press`,
  `open_application`, `get_active_window`, `find_ui_element`,
  `run_terminal_command`, `capture_build_log`, `detect_build_errors`,
  `analyze_screenshot_with_vision`, `build_with_retry`).
- New `services/mcp_client.py` — minimal MCP JSON-RPC client over stdio
  (no required new pip dep). Holds long-lived subprocesses; `MCPRegistry`
  manages logical names → clients.
- New `MCPToolCallAction` schema + `mcp_tool_call` branch in `ActionService`.
- `ActionService(mcp_registry=...)` constructor argument.
- Default command resolution: if `config.mcp.desktop_automation_command` is
  unset, `node mcp-desktop-automation/server.js` next to the version folder
  is used automatically.

### 6. Computer-use fallback (`mcp-computer-use/server.py`)
- Thin Python MCP server exposing one tool: `computer_use(goal)`.
- Strategy: try `agent-s` CLI on PATH; if missing, returns a helpful
  "install gui-agents" error so the LLM picks a different path.
- The brain service prefers structured `desktop_automation` tools and only
  reaches for `computer_use` as last resort.
- `computer_use` **always requires confirmation** (it can drive the whole GUI).

### 7. Anthropic Claude provider (`services/brain_service.py`)
- New `_call_anthropic(prompt)`. Provider chain:
  configured → openai → anthropic → groq → local_http, with `fallback_enabled`
  master switch.
- Uses **prompt caching** on the system prompt (`cache_control: ephemeral`)
  so repeat turns within 5 minutes are ~10% the cost of the cached chunk.
- Auto-picks `claude-3-5-sonnet-20241022` if user's configured model name
  doesn't look like a Claude model.
- Env var support landed in 0.7 (`ANTHROPIC_API_KEY`).

### 8. Brain context improvements
- **Date injection**: the system prompt now appends `CURRENT_DATE` and day
  of week. "Remind me tomorrow" now resolves to an actual ISO datetime.
- **MCP tool calls in the system prompt**: the LLM is taught to emit
  `mcp_tool_call` actions for desktop tasks, preferring native tools over
  the `computer_use` fallback.

### 9. Fallback chain + retries
- `_build_provider_chain()` constructs an ordered list of providers; the
  dispatcher iterates with logging; `fallback_enabled=False` honors the
  primary only. Falls back to `conversation` action only when ALL providers
  fail.

## Config surface (new sections)

```yaml
wake_word:
  enabled: false                      # off by default in 0.8
  provider: "openwakeword"            # | whisper_poll | disabled
  keyword: "daisy"
  openwakeword_model: "~/.daisy/wake/daisy.onnx"
  chunk_seconds: 1.5                  # whisper_poll
  cooldown_seconds: 3.0
reminder:
  enabled: true
  poll_seconds: 30.0
  notify_via_osascript: true
  speak_reminders: true
confirmation:
  mode: "cli"                         # cli | voice | auto_approve | auto_reject
  timeout_seconds: 30.0
mcp:
  desktop_automation_command: null    # default: node mcp-desktop-automation/server.js
  computer_use_command: null          # default: python3 mcp-computer-use/server.py
llm:
  provider: "openai"                  # openai | anthropic | groq | local_http
  anthropic_api_key: null             # or ANTHROPIC_API_KEY env var
  fallback_enabled: true              # walk the chain if primary fails
```

## New tests
- `tests/test_confirmation.py` — provider factory, CLI prompt, no-TTY rejects.
- `tests/test_reminder_scheduler.py` — past/future/recurring/invalid-JSON paths.
- `tests/test_mcp_action.py` — schema, dispatcher with mocked MCP registry,
  computer_use confirmation path.
- `tests/test_brain_anthropic.py` — provider chain, system prompt cache flag,
  primary-fail-then-fallback, default-Claude-model substitution.
- `tests/test_wake_word.py` — backend factory paths (disabled / poll / missing
  model downgrade).

## Limitations / left for 0.9
- No streaming TTS yet (Kokoro lands in 0.9).
- No RealtimeSTT migration (still using OpenAI Whisper API by default).
- No frontend — CLI / voice loop only. The Cursor-style desktop UI from the
  user's mockup lands in 0.9.
- Conversation summary compression (when history > 20) is planned, not implemented.
- Daisy-as-MCP-server (so other agents can call `listen()` / `speak()`) is
  planned for 0.9.

---

# Daisy 0.7 — Bug-Fix Release

0.7 fixes every concrete bug spotted in 0.6 without changing scope. New features
(wake word, MCP server, computer-use fallback, Anthropic provider, menu-bar) land
in 0.8 and 0.9. Goal of 0.7 = "a 0.6 that works correctly."

## Fixes

### `daisy.py`
1. Removed duplicated shebang/docstring block at top of file.
2. Removed duplicate `from schemas import TranscriptionResult` inside `process_text`.
3. **Startup greeting is now audible.** 0.6 created the TTS file but never played it.
4. `clear_old_messages` no longer runs on every message — periodic flush (every 50 messages) instead of quadratic DB churn.

### `services/voice_service.py`
5. Separate OpenAI clients for STT and TTS — an explicit `tts.openai_api_key` is honoured.
6. Replaced deprecated `tempfile.mktemp()` (race-prone) with `NamedTemporaryFile`.
7. **`_tts_piper` is implemented** (shell-out to the `piper` binary with `tts.piper_model` from config). Used to raise `NotImplementedError`.
8. macOS `say` TTS now uses the configured voice (with a small OpenAI→`say` voice map) instead of being hardcoded to "Victoria".
21. `play_audio` spawns `afplay` via `Popen` and stores the handle on `current_playback`; new `stop_playback()` method lays the groundwork for 0.8 barge-in.

### `services/brain_service.py`
9. Groq model now comes from `config.llm.model` (with a fallback to a known-good Groq model if the user picked an OpenAI-only name).
10. JSON extraction uses a brace-counting scan that survives nested objects, arrays, and braces inside string literals. The old regex broke on the very shape the system prompt asked the LLM to return.
11. OpenAI JSON-mode fallback now uses `BadRequestError` + the `param` field, with per-model caching of "JSON mode not supported" so we don't pay the failed-request cost on every call.

### `services/action_service.py`
12. Notes with the same title no longer silently overwrite — duplicate filenames get `_2`, `_3`, …
13. Removed the duplicate sqlite write path. `ActionService` now uses the shared `PersistenceLayer` so there's only one `tasks` schema.
14. Removed the redundant safety check that ran twice (dispatcher + action_service). One single defensive check remains, and the comment documents why.

### `actions/dispatcher.py`
15. **Confirmation-required actions return a failed `ActionResult` with a clear error** instead of being silently dropped. 0.8 will wire a real `ConfirmationProvider`; this fix means the user at least *sees* what got blocked today.

### `actions/safety.py`
16. **Token-aware command classification.** Substring scans replaced with `shlex` tokenisation + basename matching against named bin sets. Net effect: `curl` no longer matches inside `currently`, `su ` no longer matches inside `sudo`, and so on.
17. Whitelist enforcement now compares `basename(argv[0])` — so `/usr/bin/ls` is allowed, and every command in a pipeline (`ls | grep`) must individually be whitelisted.
22. Reordered safety checks: blocked → network → system → whitelist. This makes the previously-failing `test_network_command_blocking` pass naturally (it now reports a *network* reason, not a *whitelist* reason).

### `config/config_loader.py`
18. Removed the dead `except ImportError` branch inside `yaml.safe_load`. PyYAML is now a true conditional import with a clear error if a `.yaml` config is loaded without it installed.
19. Single `_deep_merge` helper replaces the ad-hoc merge that lost nested-dict overrides depending on key order.
20. Added env-var overrides for `ANTHROPIC_API_KEY` (used in 0.8) and `GOOGLE_API_KEY`. Existing `OPENAI_API_KEY` / `GROQ_API_KEY` behaviour unchanged.
- `LLMConfig` gains an `anthropic_api_key` field (used by 0.8's Anthropic provider).
- `TTSConfig` gains `piper_binary` / `piper_model` fields (used by fix #7).
- `Config.from_dict` is now tolerant of unknown keys (forward-compatible with 0.8/0.9 schemas).

## New tests

- `tests/test_dispatcher.py` — covers fix #15 (confirmation returns failed result; auto-approve executes).
- `tests/test_voice_service.py` — covers fixes #5, #7, #8, #21 (separate keys, Piper shell-out, configurable `say` voice, Popen handle for barge-in).
- `tests/test_safety.py` — new cases for fixes #16, #17, #22 (substring collision, absolute-path whitelist, piped command, network-reason-beats-whitelist, token-aware confirmation).
- `tests/test_brain_service.py` — new cases for fixes #9, #10 (Groq model fallback, brace-balanced JSON extractor, fenced block w/ trailing prose, braces inside strings).
- `tests/test_action_service.py` — new cases for fixes #12, #13 (note collision, shared PersistenceLayer).

## What 0.7 does NOT do

- No wake word, no barge-in (planned for 0.8).
- No MCP desktop automation server (planned for 0.8).
- No Anthropic provider integration — only the config field and env-var override (planned for 0.8).
- No Piper voice model bundled — user must download an `.onnx` model and set `tts.piper_model`.
- No menu-bar app, no Daisy-as-MCP-server, no Kokoro/RealtimeSTT (planned for 0.9).

---

# Changes from Daisy 0.5 to 0.6

## Summary

Daisy 0.6 is a complete architectural rewrite focused on structured action planning, typed schemas, and safety guardrails.

## Major Changes

### 1. Service Architecture

**Before (0.5):**
- Single monolithic `DaisyAssistant` class
- All logic in one file (`daisy-assistant.py`)
- Mixed concerns (voice, LLM, actions all together)

**After (0.6):**
- Separate service modules:
  - `VoiceService`: STT and TTS
  - `BrainService`: Action planning
  - `ActionService`: Action execution
  - `SafetyChecker`: Permission validation
  - `ActionDispatcher`: Orchestration
- Clean boundaries between components
- Testable, modular design

### 2. Typed Schemas

**Before (0.5):**
- Loose dataclasses
- No validation
- Free-form LLM responses

**After (0.6):**
- Pydantic models for all data structures:
  - `TranscriptionResult`
  - `AssistantIntent`
  - `AssistantAction` (union type)
  - `ActionResult`
- JSON schema validation
- Type safety throughout

### 3. Action Planning

**Before (0.5):**
- LLM returns free-form text
- Heuristic parsing for commands
- No structured actions

**After (0.6):**
- LLM outputs validated JSON schema
- Structured action types:
  - `create_note`
  - `create_task`
  - `create_reminder`
  - `run_command`
  - `conversation`
- Explicit action contracts

### 4. Safety & Permissions

**Before (0.5):**
- Basic preference-based rules
- No command validation
- No permission system

**After (0.6):**
- Command whitelisting/blocklisting
- Directory restrictions
- Confirmation requirements
- Network/system command blocking
- Safety checker layer

### 5. Audit Logging

**Before (0.5):**
- Conversation history saved as JSON
- No action logging
- No decision tracking

**After (0.6):**
- Append-only audit log (JSONL)
- Logs all transcriptions, intents, actions, executions
- Timestamped audit trail
- Configurable logging

### 6. Configuration

**Before (0.5):**
- JSON config file
- Manual configuration
- Limited options

**After (0.6):**
- YAML/JSON config support
- Environment variable overrides
- Structured config with dataclasses
- Local-first endpoint configuration

### 7. Persistence

**Before (0.5):**
- Conversation JSON files
- No structured storage

**After (0.6):**
- SQLite database for tasks and memory
- Markdown tasks file (human-readable)
- JSON reminders
- Conversation history in database
- Configurable retention

### 8. Action Execution

**Before (0.5):**
- Heuristic command detection
- macOS-specific automation scripts
- Limited action types

**After (0.6):**
- Structured action dispatcher
- First-class action types:
  - Notes (markdown files)
  - Tasks (file + database)
  - Reminders (JSON + future calendar)
  - Commands (with safety checks)
- Platform-agnostic (mostly)

## What's Preserved

- Voice conversation loop (mic → STT → LLM → TTS)
- OpenAI Whisper STT support
- OpenAI/Groq LLM support
- OpenAI TTS support
- Conversation history/memory
- Basic configuration system

## What's Improved

- **Structure**: Clean service boundaries
- **Safety**: Permission system with guardrails
- **Typing**: Pydantic schemas throughout
- **Actions**: Structured action planning
- **Logging**: Comprehensive audit trail
- **Config**: More flexible configuration
- **Storage**: SQLite + files for persistence

## Migration Guide

### Config Migration

Old config (`~/.daisy/config.json`):
```json
{
  "openai_api_key": "...",
  "llm_model": "gpt-4",
  "voice": "nova"
}
```

New config (`~/.daisy/config.yaml`):
```yaml
stt:
  provider: "openai"
  openai_api_key: null  # Set via env var

llm:
  provider: "openai"
  model: "gpt-4"
  openai_api_key: null  # Set via env var

tts:
  provider: "openai"
  voice: "nova"
```

### API Changes

**Before:**
```python
assistant = DaisyAssistant()
assistant.speak_and_listen_loop()
```

**After:**
```python
from daisy import DaisyPipeline

pipeline = DaisyPipeline()
pipeline.voice_loop()
```

### Action Usage

**Before:** LLM responds with free-form text

**After:** LLM returns structured JSON actions:
```json
{
  "actions": [{
    "action_type": "create_note",
    "create_note": {
      "title": "Python Notes",
      "content": "..."
    }
  }]
}
```

## Breaking Changes

1. **Class structure**: `DaisyAssistant` → `DaisyPipeline` with services
2. **Config format**: JSON → YAML (JSON still supported)
3. **Import paths**: All imports changed
4. **Action format**: Free-form → Structured JSON schemas
5. **CLI**: Some command-line arguments changed

## Feature Parity

Most features from 0.5 are preserved or improved:
- ✅ Voice conversation
- ✅ Text conversation
- ✅ Conversation memory
- ✅ LLM fallback (OpenAI → Groq)
- ✅ STT fallback (OpenAI → Google)
- ⚠️ macOS-specific automation (moved to separate module, not in 0.6 yet)
- ⚠️ MCP desktop automation (separate, can be integrated)

## Future Improvements (Not in 0.6)

- User confirmation prompts (currently logged and skipped)
- Calendar integration for reminders
- Web UI for viewing tasks/notes
- Voice interrupt handling
- Better error recovery
- Test harness with golden tests
- More action types (email, calendar, etc.)

