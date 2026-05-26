# Daisy Assistant 1.0

A structured AI assistant with action planning, safety guardrails, and typed schemas.

## Architecture

Daisy 0.6 implements a clean service architecture with typed contracts:

```
┌──────────────┐
│ Voice Input  │ (Microphone or Audio File)
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Voice Service   │ (STT: OpenAI/Groq/Local HTTP)
└──────┬───────────┘
       │ TranscriptionResult
       ▼
┌──────────────────┐
│  Brain Service   │ (LLM: OpenAI/Groq/Local HTTP)
└──────┬───────────┘
       │ AssistantIntent (with AssistantActions)
       ▼
┌──────────────────┐
│ Safety Checker   │ (Whitelists, Blocklists, Permissions)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Action Dispatcher│ (Execute: Note, Task, Reminder, Command)
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Action Service   │ (Creates notes, tasks, reminders, runs commands)
└──────────────────┘
```

## Features

### ✅ Service Architecture
- **VoiceService**: STT with local/cloud fallback
- **BrainService**: Action planner with JSON schema output
- **ActionService**: Dispatcher for structured actions
- **SafetyChecker**: Permission layer with whitelists/blocklists

### ✅ Typed Contracts (Pydantic)
- `TranscriptionResult`: STT output
- `AssistantIntent`: Structured intent with actions
- `AssistantAction`: Union of action types (create_note, create_task, create_reminder, run_command, conversation)
- `ActionResult`: Execution results

### ✅ Action Types
- **CreateNote**: Write markdown notes to configured directory
- **CreateTask**: Append to tasks file + SQLite database
- **CreateReminder**: Save reminders with timestamps
- **RunCommand**: Execute terminal commands (with safety checks)
- **Conversation**: Natural conversation responses

### ✅ Safety & Permissions
- Whitelisted commands and directories
- Blocked command patterns (rm -rf, etc.)
- Confirmation requirements for dangerous actions
- Network/system-modifying command blocking

### ✅ Audit Logging
- Append-only audit log (JSONL format)
- Logs all transcriptions, intents, actions, and executions
- Timestamped entries for full audit trail

### ✅ Configuration
- YAML/JSON config support
- Environment variable overrides
- Local-first endpoints (with cloud fallback)
- Configurable paths, models, and providers

### ✅ Persistence
- SQLite database for tasks and conversation memory
- Markdown tasks file (human-readable)
- JSON reminders file
- Conversation history with configurable retention

## Installation

```bash
cd "Daisy -AI Assistant- 0.6"
./setup.sh
```

## Configuration

Create/edit `~/.daisy/config.yaml`:

```yaml
stt:
  provider: "openai"  # openai, google, local_http
  openai_api_key: null  # Set via OPENAI_API_KEY env var
  
llm:
  provider: "openai"  # openai, groq, local_http
  model: "gpt-4"
  openai_api_key: null  # Set via OPENAI_API_KEY env var
  
tts:
  provider: "openai"
  voice: "nova"
  
safety:
  whitelisted_commands: []
  whitelisted_directories: []
  blocked_commands:
    - "rm -rf"
    - "del /f"
  require_confirmation_for:
    - "rm"
    - "del"
    
paths:
  notes_directory: "~/.daisy/notes"
  tasks_file: "~/.daisy/tasks.md"
  reminders_file: "~/.daisy/reminders.json"
  audit_log: "~/.daisy/audit.log"
  database_path: "~/.daisy/daisy.db"
```

## Usage

### Voice Mode (Interactive)
```bash
python3 daisy.py
```

### Text Mode (Interactive)
```bash
python3 daisy.py --text
```

### Process Text (One-shot)
```bash
python3 daisy.py --input "Create a note about Python best practices"
```

### Process Audio File
```bash
python3 daisy.py --audio recording.wav
```

## What's New in 0.6

### Structured Action Planning
- LLM outputs validated JSON schemas
- Actions are typed (Pydantic models)
- Clear separation between conversation and actions

### Safety First
- Command whitelisting
- Directory restrictions
- Confirmation requirements
- Audit logging of all decisions

### Local-First
- Support for local HTTP endpoints (STT, LLM, TTS)
- Fallback to cloud providers
- Configurable provider chain

### Better Architecture
- Service modules (voice, brain, action)
- Clean boundaries between components
- Testable, modular design

## Differences from 0.5

**0.5**: Monolithic `daisy-assistant.py` with free-form LLM responses
**0.6**: Structured services with typed action schemas and safety guardrails

**0.5**: Manual conversation handling
**0.6**: Action planner with structured outputs (notes, tasks, reminders, commands)

**0.5**: Basic automation hooks
**0.6**: Full action dispatcher with safety checks and audit logging

## Next Steps

- [ ] Add confirmation prompts for dangerous actions
- [ ] Implement calendar integration for reminders
- [ ] Add test harness with golden tests
- [ ] Support for more action types
- [ ] Web UI for viewing tasks/notes
- [ ] Voice interrupt handling
- [ ] Better error recovery

