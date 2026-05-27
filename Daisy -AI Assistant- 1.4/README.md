# Daisy 1.4 — Undo + log viewer + settings

You can say "undo" and Daisy actually undoes the last thing she did — deletes the note, removes the task, cancels the reminder, or forgets the fact you just told her. You can also see a log of everything she's done recently, and ask her current settings (which voice, which AI provider, etc).

## New in 1.4

- **`services/undo_stack.py`** — LIFO `UndoStack` (cap 50) + `UndoManager`
- **Reversible action types**:
  - `create_note` → delete file
  - `create_task` → remove line from tasks.md
  - `create_reminder` → remove from reminders.json
  - `memory_remember` → forget from `MemoryStore`
- **Not reversible** (returns explanatory error): `send_email`, `create_calendar_event` (asks user to delete manually), `run_command`
- **`DaisyPipeline._push_undo()`** called after every successful action result
- **API endpoints**:
  - `GET /api/undo` — list undo stack
  - `POST /api/undo` — execute undo of most recent action
  - `GET /api/log?lines=N` — tail audit log (JSONL parsed)
  - `GET /api/settings` — read current config as flat dict
- 16 new tests

## Tests

189/189 passing.
