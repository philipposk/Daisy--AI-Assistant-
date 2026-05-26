"""Undo stack for Daisy (1.4).

Tracks reversible actions so the user can say/click "undo".

Supported undoable action types:
  - create_note       → delete the created file
  - create_task       → remove last line from tasks.md + delete from DB
  - create_reminder   → remove from reminders.json
  - memory_remember   → delete from memory store
  - run_command       → not undoable (logged but noop)

The stack is in-memory only (lost on restart); it holds up to `max_size` entries.
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from utils import get_logger

logger = get_logger("undo_stack")

MAX_STACK_SIZE = 50


@dataclass
class UndoEntry:
    action_type: str
    description: str
    metadata: dict = field(default_factory=dict)   # action-specific undo data


class UndoStack:
    """In-memory LIFO undo stack."""

    def __init__(self, max_size: int = MAX_STACK_SIZE):
        self._stack: deque[UndoEntry] = deque(maxlen=max_size)

    def push(self, entry: UndoEntry) -> None:
        self._stack.append(entry)
        logger.debug("Undo push: %s", entry.description)

    def peek(self) -> Optional[UndoEntry]:
        return self._stack[-1] if self._stack else None

    def pop(self) -> Optional[UndoEntry]:
        if not self._stack:
            return None
        entry = self._stack.pop()
        logger.debug("Undo pop: %s", entry.description)
        return entry

    def list(self) -> list[dict]:
        """Return stack as list (most recent last)."""
        return [
            {"action_type": e.action_type, "description": e.description}
            for e in self._stack
        ]

    def __len__(self):
        return len(self._stack)


# ---------------------------------------------------------------------------
# UndoManager — knows how to actually reverse each action type
# ---------------------------------------------------------------------------

class UndoManager:
    """
    Executes undo for a popped UndoEntry.

    Needs access to the config to know where notes/tasks/reminders live.
    """

    def __init__(self, config, memory_store=None):
        self.config = config
        self.memory_store = memory_store

    def execute(self, entry: UndoEntry) -> dict:
        """
        Execute the undo. Returns {"ok": bool, "description": str, "error": str|None}.
        """
        try:
            if entry.action_type == "create_note":
                return self._undo_create_note(entry)
            elif entry.action_type == "create_task":
                return self._undo_create_task(entry)
            elif entry.action_type == "create_reminder":
                return self._undo_create_reminder(entry)
            elif entry.action_type == "memory_remember":
                return self._undo_memory_remember(entry)
            elif entry.action_type == "create_calendar_event":
                return {"ok": False, "description": entry.description,
                        "error": "Calendar events cannot be auto-undone; please delete manually."}
            elif entry.action_type == "send_email":
                return {"ok": False, "description": entry.description,
                        "error": "Sent emails cannot be unsent."}
            else:
                return {"ok": False, "description": entry.description,
                        "error": f"Undo not supported for action type: {entry.action_type}"}
        except Exception as exc:
            logger.error("Undo failed: %s", exc, exc_info=True)
            return {"ok": False, "description": entry.description, "error": str(exc)}

    def _undo_create_note(self, entry: UndoEntry) -> dict:
        path = Path(entry.metadata.get("path", ""))
        if not path.exists():
            return {"ok": True, "description": entry.description,
                    "error": "Note file already gone"}
        path.unlink()
        return {"ok": True, "description": f"Deleted note: {path.name}", "error": None}

    def _undo_create_task(self, entry: UndoEntry) -> dict:
        """Remove the last matching line from tasks.md."""
        tasks_file = Path(self.config.paths.tasks_file).expanduser()
        title = entry.metadata.get("title", "")
        if not tasks_file.exists():
            return {"ok": False, "description": entry.description, "error": "Tasks file not found"}
        lines = tasks_file.read_text().splitlines(keepends=True)
        # Remove last line containing the task title (search from end)
        removed = False
        for i in range(len(lines) - 1, -1, -1):
            if title and title in lines[i]:
                lines.pop(i)
                removed = True
                break
        if not removed:
            return {"ok": False, "description": entry.description, "error": "Task line not found"}
        tasks_file.write_text("".join(lines))
        return {"ok": True, "description": f"Removed task: {title}", "error": None}

    def _undo_create_reminder(self, entry: UndoEntry) -> dict:
        """Remove reminder by message from reminders.json."""
        reminders_file = Path(self.config.paths.reminders_file).expanduser()
        message = entry.metadata.get("message", "")
        if not reminders_file.exists():
            return {"ok": True, "description": entry.description, "error": None}
        try:
            data = json.loads(reminders_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {"ok": False, "description": entry.description, "error": "Could not read reminders file"}
        before = len(data)
        data = [r for r in data if r.get("message") != message]
        reminders_file.write_text(json.dumps(data, indent=2))
        removed = before - len(data)
        return {"ok": True, "description": f"Removed {removed} reminder(s): {message}", "error": None}

    def _undo_memory_remember(self, entry: UndoEntry) -> dict:
        topic = entry.metadata.get("topic", "")
        if self.memory_store is None:
            return {"ok": False, "description": entry.description, "error": "No memory store available"}
        found = self.memory_store.forget(topic)
        if not found:
            return {"ok": False, "description": entry.description, "error": f"Memory '{topic}' not found"}
        return {"ok": True, "description": f"Forgot memory: {topic}", "error": None}
