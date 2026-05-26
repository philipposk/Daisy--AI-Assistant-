# Daisy Assistant 0.6 - Quick Start Guide

## What's New

Daisy 0.6 is a complete rewrite with a structured service architecture:

- ✅ **Typed schemas** (Pydantic models) for all data structures
- ✅ **Action planning** - LLM outputs structured JSON actions
- ✅ **Safety layer** - Whitelists, blocklists, confirmation requirements
- ✅ **Audit logging** - Full audit trail of all actions
- ✅ **Service architecture** - Clean separation: Voice → Brain → Actions
- ✅ **Local-first** - Support for local HTTP endpoints with cloud fallback

## Installation

1. **Install dependencies:**
   ```bash
   cd "Daisy -AI Assistant- 0.6"
   ./setup.sh
   ```

2. **Set API keys:**
   ```bash
   export OPENAI_API_KEY='your-key-here'
   # Optional: export GROQ_API_KEY='your-key-here'
   ```

3. **Run Daisy:**
   ```bash
   python3 daisy.py              # Voice mode
   python3 daisy.py --text       # Text mode
   ```

## Configuration

Edit `~/.daisy/config.yaml` after first run, or create it manually:

```yaml
llm:
  provider: "openai"
  model: "gpt-4"
  
safety:
  whitelisted_commands:
    - "ls"
    - "pwd"
    - "cd"
  blocked_commands:
    - "rm -rf"
    - "sudo"
```

## Usage Examples

### Voice Conversation
```bash
python3 daisy.py
# Say: "Create a note about Python async programming"
# Daisy will create a markdown note in ~/.daisy/notes/
```

### Text Conversation
```bash
python3 daisy.py --text
# Type: "Create a task to review pull requests"
# Daisy will add a task to ~/.daisy/tasks.md
```

### One-shot Processing
```bash
python3 daisy.py --input "Remind me to call mom tomorrow"
```

## Action Types

Daisy understands these action types:

1. **Create Note**: "Take a note about X", "Save this: ..."
2. **Create Task**: "Add a task to...", "I need to...", "Remind me to..."
3. **Create Reminder**: "Remind me at 3pm to...", "Set a reminder..."
4. **Run Command**: "Run ls -la", "Execute python script.py"
5. **Conversation**: General chat, questions, etc.

## Safety Features

- Commands are checked against whitelist/blocklist
- Dangerous commands require confirmation
- All actions are logged to audit log
- Working directory restrictions

## File Locations

- Config: `~/.daisy/config.yaml`
- Notes: `~/.daisy/notes/*.md`
- Tasks: `~/.daisy/tasks.md`
- Reminders: `~/.daisy/reminders.json`
- Database: `~/.daisy/daisy.db`
- Audit Log: `~/.daisy/audit.log`

## Troubleshooting

**No microphone access:**
- Use `--text` mode
- Or check macOS privacy settings for microphone

**API key errors:**
- Set `OPENAI_API_KEY` environment variable
- Or edit `~/.daisy/config.yaml`

**Import errors:**
- Run `pip install -r requirements.txt`
- Make sure you're in the correct directory

## Next Steps

- Review `README.md` for full architecture details
- Customize `~/.daisy/config.yaml` for your needs
- Add commands to whitelist for automation
- Check `~/.daisy/audit.log` to see all actions

