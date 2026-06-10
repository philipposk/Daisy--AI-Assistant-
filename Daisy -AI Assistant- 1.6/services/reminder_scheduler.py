"""
Reminder scheduler (0.8).

Background thread that polls `reminders.json` and fires due reminders. Recurring
reminders are re-scheduled (24h cadence by default). Fires via:
- macOS osascript `display notification` (configurable)
- TTS through the supplied VoiceService (configurable)

The file format matches what `ActionService._execute_create_reminder` writes:
[
  {
    "message": "...",
    "reminder_time": "2026-05-26T10:00:00",   # ISO; if null/empty, never fires
    "recurring": false,
    "created_at": "...",
    "_fired": false                            # added by the scheduler
  }
]
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from utils import get_logger

logger = get_logger("reminder_scheduler")


class ReminderScheduler:
    """Polls a JSON file and fires reminders whose time has passed."""

    def __init__(
        self,
        reminders_path: Path,
        voice_service=None,
        poll_seconds: float = 30.0,
        notify_via_osascript: bool = True,
        speak_reminders: bool = True,
        recurring_interval: timedelta = timedelta(days=1),
    ):
        self.path = Path(reminders_path).expanduser()
        self.voice = voice_service
        self.poll_seconds = poll_seconds
        self.notify_via_osascript = notify_via_osascript
        self.speak_reminders = speak_reminders
        self.recurring_interval = recurring_interval

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ----------------- lifecycle -----------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ReminderScheduler")
        self._thread.start()
        logger.info(f"Reminder scheduler started (poll every {self.poll_seconds}s).")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    # ----------------- main loop -----------------

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Reminder tick failed: {e}", exc_info=True)
            self._stop_event.wait(self.poll_seconds)

    def tick(self) -> int:
        """One scheduler iteration. Returns number of reminders fired.

        1.6: the whole read-modify-write cycle runs under the shared
        reminders lock (services.reminders_store) so a reminder created by
        ActionService mid-tick can't be clobbered, and the write is atomic.
        Firing (notification + TTS) happens after the lock is released so a
        slow TTS call can't block reminder creation.
        """
        from services.reminders_store import reminders_lock, read_reminders, write_reminders

        to_fire: list[dict] = []
        now = datetime.now()
        fired = 0

        with reminders_lock():
            if not self.path.exists():
                return 0
            reminders = read_reminders(self.path)
            if not reminders:
                return 0

            dirty = False
            for entry in reminders:
                if not isinstance(entry, dict):
                    continue
                if entry.get("_fired") and not entry.get("recurring"):
                    continue

                t_str = entry.get("reminder_time")
                if not t_str:
                    continue
                try:
                    due = datetime.fromisoformat(t_str)
                except ValueError:
                    # Future: support natural language via dateparser; for now skip.
                    continue

                if now < due:
                    continue

                to_fire.append(dict(entry))
                fired += 1
                dirty = True

                if entry.get("recurring"):
                    # Re-schedule for next cycle
                    next_due = due + self.recurring_interval
                    while next_due <= now:
                        next_due += self.recurring_interval
                    entry["reminder_time"] = next_due.isoformat()
                    entry["_fired"] = False
                else:
                    entry["_fired"] = True

            if dirty:
                try:
                    write_reminders(self.path, reminders)
                except Exception as e:
                    logger.warning(f"Failed to write reminders.json: {e}")

        for entry in to_fire:
            self._fire(entry)

        return fired

    # ----------------- firing -----------------

    def _fire(self, entry: dict) -> None:
        msg = entry.get("message", "Reminder")
        logger.info(f"Firing reminder: {msg!r}")

        if self.notify_via_osascript:
            try:
                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'display notification "{_escape(msg)}" with title "Daisy reminder"',
                    ],
                    check=False, capture_output=True,
                )
            except FileNotFoundError:
                pass  # not on macOS

        if self.speak_reminders and self.voice is not None:
            try:
                audio_path = self.voice.text_to_speech(f"Reminder: {msg}")
                self.voice.play_audio(audio_path, wait=False, track=False)
            except Exception as e:
                logger.warning(f"TTS reminder failed: {e}")


def _escape(s: str) -> str:
    """Escape for AppleScript double-quoted string."""
    return s.replace("\\", "\\\\").replace("\"", "\\\"")
