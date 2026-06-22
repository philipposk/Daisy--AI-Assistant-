"""Undo stack for Daisy (1.4).

Tracks reversible actions so the user can say/click "undo".

Supported undoable action types:
  - create_note       → delete the created file
  - create_task       → remove last line from tasks.md + delete from DB
  - create_reminder   → remove from reminders.json
  - memory_remember   → delete from memory store
  - run_command       → not undoable (logged but noop)

1.6: the stack persists to a JSON file (default `~/.daisy/undo.json`) so
"undo" still works after a crash or launchd restart — the headline feature
used to silently die on every auto-restart.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import deque
from dataclasses import dataclass, field, asdict
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
    """LIFO undo stack, optionally persisted to a JSON file across restarts."""

    def __init__(self, max_size: int = MAX_STACK_SIZE, persist_path: Optional[Path] = None):
        self._stack: deque[UndoEntry] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._persist_path = Path(persist_path).expanduser() if persist_path else None
        self._load()

    def push(self, entry: UndoEntry) -> None:
        with self._lock:
            self._stack.append(entry)
            self._save()
        logger.debug("Undo push: %s", entry.description)

    def peek(self) -> Optional[UndoEntry]:
        with self._lock:
            return self._stack[-1] if self._stack else None

    def pop(self) -> Optional[UndoEntry]:
        with self._lock:
            if not self._stack:
                return None
            entry = self._stack.pop()
            self._save()
        logger.debug("Undo pop: %s", entry.description)
        return entry

    def list(self) -> list[dict]:
        """Return stack as list (most recent last)."""
        with self._lock:
            return [
                {"action_type": e.action_type, "description": e.description}
                for e in self._stack
            ]

    def __len__(self):
        with self._lock:
            return len(self._stack)

    # ----------------- persistence -----------------

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            raw = json.loads(self._persist_path.read_text() or "[]")
            for item in raw[-self._stack.maxlen:]:
                self._stack.append(UndoEntry(
                    action_type=item.get("action_type", ""),
                    description=item.get("description", ""),
                    metadata=item.get("metadata") or {},
                ))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load undo stack: %s", exc)

    def _save(self) -> None:
        """Atomic write; caller holds self._lock."""
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=str(self._persist_path.parent), prefix=".undo-", suffix=".tmp"
            )
            with os.fdopen(fd, "w") as f:
                json.dump([asdict(e) for e in self._stack], f, indent=2)
            os.replace(tmp, self._persist_path)
        except OSError as exc:
            logger.warning("Could not persist undo stack: %s", exc)


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
        """Remove THE reminder created by this entry from reminders.json.

        1.6: match on created_at when available so two reminders with the
        same message don't both get deleted; otherwise remove only the last
        message match. All IO goes through the shared reminders store.
        """
        from services.reminders_store import reminders_lock, read_reminders, write_reminders
        reminders_file = Path(self.config.paths.reminders_file).expanduser()
        message = entry.metadata.get("message", "")
        created_at = entry.metadata.get("created_at")

        with reminders_lock():
            if not reminders_file.exists():
                return {"ok": True, "description": entry.description, "error": None}
            data = read_reminders(reminders_file)

            idx = None
            if created_at:
                for i in range(len(data) - 1, -1, -1):
                    if data[i].get("created_at") == created_at:
                        idx = i
                        break
            if idx is None:
                for i in range(len(data) - 1, -1, -1):
                    if data[i].get("message") == message:
                        idx = i
                        break

            if idx is None:
                return {"ok": False, "description": entry.description,
                        "error": "Reminder not found (already removed?)"}

            data.pop(idx)
            write_reminders(reminders_file, data)

        return {"ok": True, "description": f"Removed reminder: {message}", "error": None}

    def _undo_memory_remember(self, entry: UndoEntry) -> dict:
        topic = entry.metadata.get("topic", "")
        if self.memory_store is None:
            return {"ok": False, "description": entry.description, "error": "No memory store available"}
        found = self.memory_store.forget(topic)
        if not found:
            return {"ok": False, "description": entry.description, "error": f"Memory '{topic}' not found"}
        return {"ok": True, "description": f"Forgot memory: {topic}", "error": None}
