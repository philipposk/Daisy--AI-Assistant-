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

