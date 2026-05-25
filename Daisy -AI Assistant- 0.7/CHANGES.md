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

