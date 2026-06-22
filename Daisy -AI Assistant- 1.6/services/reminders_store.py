"""Shared, thread-safe access to reminders.json (1.6).

Both ActionService (creates reminders) and ReminderScheduler (fires and
rewrites them) used to do independent read-modify-write cycles on the same
file from different threads — a freshly created reminder could be clobbered
by the scheduler's write, or a fired flag lost.

All readers/writers now go through this module: one process-wide lock plus
atomic replace-on-write so a crash mid-write can't truncate the file.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

_LOCK = threading.RLock()


def reminders_lock() -> threading.RLock:
    """The process-wide lock guarding reminders.json read-modify-write cycles."""
    return _LOCK


def read_reminders(path: Path) -> list:
    """Read the reminders list; returns [] on missing/corrupt file."""
    path = Path(path).expanduser()
    with _LOCK:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text() or "[]")
        except (json.JSONDecodeError, OSError):
            return []
        return data if isinstance(data, list) else []


def write_reminders(path: Path, reminders: list) -> None:
    """Atomically replace the reminders file (temp file + os.replace)."""
    path = Path(path).expanduser()
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=".reminders-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(reminders, f, indent=2)
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
