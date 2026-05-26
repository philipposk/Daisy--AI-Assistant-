# Daisy Assistant 0.6 - Architecture

## Overview

Daisy 0.6 implements a clean vertical slice architecture with typed schemas and service boundaries:

```
Voice Input → Voice Service (STT) → Brain Service (LLM) → Action Dispatcher → Action Service → Output
```

## Service Architecture

### Voice Service (`services/voice_service.py`)
- **Responsibility**: Speech-to-Text and Text-to-Speech
- **Input**: Audio files or microphone input
- **Output**: `TranscriptionResult` (text, language, confidence)
- **Providers**: OpenAI Whisper, Google Speech, Local HTTP endpoints
- **Fallback**: Automatic fallback chain if primary provider fails

### Brain Service (`services/brain_service.py`)
- **Responsibility**: Convert transcripts to structured actions
- **Input**: `TranscriptionResult` + conversation history
- **Output**: `AssistantIntent` (with list of `AssistantAction`)
- **LLM**: OpenAI GPT-4, Groq, or local HTTP (Ollama)
- **Output Format**: Validated JSON schema matching action types

### Action Dispatcher (`actions/dispatcher.py`)
- **Responsibility**: Orchestrate action execution with safety checks
- **Input**: List of `AssistantAction`
- **Process**: 
  1. Safety checks (SafetyChecker)
  2. Confirmation requirements
  3. Audit logging
  4. Action execution (ActionService)
- **Output**: List of `ActionResult`

### Action Service (`services/action_service.py`)
- **Responsibility**: Execute structured actions
- **Action Types**:
  - `create_note`: Write markdown files
  - `create_task`: Append to tasks file + SQLite
  - `create_reminder`: Save to reminders JSON
  - `run_command`: Execute terminal commands
  - `conversation`: Return response text

### Safety Checker (`actions/safety.py`)
- **Responsibility**: Permission and safety validation
- **Checks**:
  - Command whitelist/blocklist
  - Directory restrictions
  - Network/system-modifying command blocking
  - Confirmation requirements

## Data Models (Pydantic Schemas)

### `TranscriptionResult`
```python
{
    "text": str,
    "language": Optional[str],
    "confidence": Optional[float],
    "timestamp": datetime
}
```

### `AssistantAction`
Union type with one of:
- `create_note`: CreateNoteAction (title, content, path, tags)
- `create_task`: CreateTaskAction (title, description, priority, due_date, tags)
- `create_reminder`: CreateReminderAction (message, reminder_time, recurring)
- `run_command`: RunCommandAction (command, working_directory, timeout, confirmation_required)
- `conversation`: str (free-form response)

### `AssistantIntent`
```python
{
    "transcript": str,
    "actions": List[AssistantAction],
    "requires_confirmation": bool,
    "timestamp": datetime
}
```

### `ActionResult`
```python
{
    "action": AssistantAction,
    "success": bool,
    "output": Optional[str],
    "error": Optional[str],
    "timestamp": datetime,
    "execution_time": Optional[float]
}
```

## Configuration

Configuration is loaded from `~/.daisy/config.yaml` with environment variable overrides.

**Structure:**
- `stt`: STT provider configuration
- `llm`: LLM provider configuration
- `tts`: TTS provider configuration
- `safety`: Safety/permission settings
- `paths`: File/directory paths

## Persistence

### SQLite Database (`~/.daisy/daisy.db`)
- `tasks` table: Task storage with metadata
- `conversation_memory` table: Recent conversation history

### Files
- `tasks.md`: Human-readable task list (markdown)
- `reminders.json`: Reminder storage (JSON)
- `notes/*.md`: Individual note files (markdown)
- `audit.log`: Append-only audit log (JSONL)

## Audit Logging

All significant events are logged to `~/.daisy/audit.log` (JSONL format):

- `transcription`: STT results
- `intent`: Structured intents from brain service
- `action_decision`: Approval/denial of actions
- `execution`: Action execution results
- `error`: Errors and exceptions

## Flow Example

1. **User speaks**: "Create a note about async Python"

2. **Voice Service**: 
   - Records audio → Transcribes → Returns `TranscriptionResult(text="Create a note about async Python")`

3. **Brain Service**:
   - Receives transcript + conversation history
   - Calls LLM with system prompt for action planning
   - LLM returns JSON: `{"actions": [{"action_type": "create_note", "create_note": {...}}]}`
   - Parses and validates → Returns `AssistantIntent`

4. **Action Dispatcher**:
   - Receives `AssistantIntent` with actions
   - For each action:
     - Safety check (allowed? requires confirmation?)
     - Log decision to audit log
     - Execute via Action Service
     - Log execution result

5. **Action Service**:
   - Executes `create_note` action
   - Creates markdown file in `~/.daisy/notes/`
   - Returns `ActionResult(success=True, output="Created note at ...")`

6. **Response**:
   - Build response from action results
   - Add to conversation history
   - Return text for TTS

## Safety Architecture

### Command Safety
- **Whitelist**: Only allowed commands (if whitelist is configured)
- **Blocklist**: Always-blocked patterns (rm -rf, sudo, etc.)
- **Network blocking**: Blocks curl, wget, ssh, etc.
- **System blocking**: Blocks sudo, chmod, mount, etc.

### Directory Safety
- **Whitelist**: Only execute commands in allowed directories
- **Validation**: Check directory exists and is actually a directory

### Confirmation Requirements
- Commands with dangerous patterns require confirmation
- `confirmation_required` flag in action can force confirmation
- Currently logged and skipped if not auto-approved (future: user prompt)

## Extension Points

### Adding New Action Types
1. Add new action model to `schemas/models.py` (e.g., `CreateCalendarEventAction`)
2. Add to `AssistantAction` union type
3. Update `BrainService` system prompt and parsing
4. Add executor method to `ActionService`
5. Update `ActionDispatcher` if needed

### Adding New Providers
1. Add provider config to `Config` dataclass
2. Implement provider method in service (e.g., `_call_custom_llm`)
3. Add provider check in service initialization
4. Update fallback chain

### Custom Safety Rules
1. Extend `SafetyChecker` class
2. Add new check methods
3. Update `check_action` to call new checks
4. Update config schema if needed

## Testing Strategy

Future improvements should include:

1. **Golden Tests**: Test JSON action parsing with known good/bad examples
2. **Safety Tests**: Test command blocking/allowing with various inputs
3. **Integration Tests**: Test full pipeline with mocked services
4. **Unit Tests**: Test individual service methods

## Comparison to 0.5

**0.5**: Monolithic class with mixed concerns
**0.6**: Separate services with clear boundaries

**0.5**: Free-form LLM responses
**0.6**: Structured JSON action schemas

**0.5**: Manual action handling
**0.6**: Typed action dispatcher with safety checks

**0.5**: Basic conversation logging
**0.6**: Full audit logging of all decisions

