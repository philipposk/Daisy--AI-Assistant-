# Daisy 0.6 — Clean rewrite

The first version of Daisy with a proper structure. Instead of one giant Python file, she has separate modules for listening, thinking, and doing things. Remembers conversations across sessions in a small database, logs everything she does, and has guardrails against running anything destructive.

## What changed vs 0.5

- Monolithic `daisy-assistant.py` → service architecture (Voice / Brain / Action / Safety / Dispatch)
- Free-form LLM output → Pydantic-typed JSON schemas (`AssistantIntent`, `AssistantAction`, `ActionResult`)
- Inline DB calls → shared `PersistenceLayer` (SQLite for tasks + conversation memory)
- Ad-hoc logging → append-only JSONL audit log
- Hardcoded settings → YAML/JSON config + env-var overrides

## Action types

- `create_note` → markdown file in notes dir
- `create_task` → tasks.md + SQLite
- `create_reminder` → reminders.json
- `run_command` → shell exec (with safety check)
- `conversation` → free-form reply

## Safety

- Whitelisted commands / directories
- Blocked patterns (`rm -rf`, etc.)
- Confirmation required for destructive actions

## Quick start

```bash
./setup.sh
python3 daisy.py --text                    # text loop
python3 daisy.py --input "make a note"     # one-shot
python3 daisy.py                            # voice loop (mic + OPENAI_API_KEY required)
```

## Tests

41 tests (1 known failing — fixed in 0.7).
