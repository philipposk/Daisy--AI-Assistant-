"""
Tests for ReminderScheduler (0.8).
"""
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from services.reminder_scheduler import ReminderScheduler


def _write(path: Path, payload):
    path.write_text(json.dumps(payload))


def test_fires_past_due_reminder():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "reminders.json"
        past = (datetime.now() - timedelta(minutes=5)).isoformat()
        _write(p, [{"message": "drink water", "reminder_time": past, "recurring": False}])

        sched = ReminderScheduler(
            reminders_path=p,
            voice_service=None,
            notify_via_osascript=False,
            speak_reminders=False,
        )
        fired = sched.tick()
        assert fired == 1

        # Re-tick should not fire again (marked _fired)
        again = sched.tick()
        assert again == 0


def test_future_reminder_not_fired():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "reminders.json"
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        _write(p, [{"message": "later", "reminder_time": future}])
        sched = ReminderScheduler(reminders_path=p, voice_service=None,
                                  notify_via_osascript=False, speak_reminders=False)
        assert sched.tick() == 0


def test_recurring_reminder_reschedules():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "reminders.json"
        past = (datetime.now() - timedelta(days=2)).isoformat()
        _write(p, [{"message": "daily", "reminder_time": past, "recurring": True}])
        sched = ReminderScheduler(
            reminders_path=p, voice_service=None,
            notify_via_osascript=False, speak_reminders=False,
            recurring_interval=timedelta(days=1),
        )
        fired = sched.tick()
        assert fired == 1

        data = json.loads(p.read_text())
        new_due = datetime.fromisoformat(data[0]["reminder_time"])
        # Next due must be in the future after firing
        assert new_due > datetime.now()


def test_voice_speak_called():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "reminders.json"
        past = (datetime.now() - timedelta(minutes=1)).isoformat()
        _write(p, [{"message": "speak me", "reminder_time": past, "recurring": False}])

        voice = MagicMock()
        voice.text_to_speech.return_value = Path("/tmp/fake.mp3")
        sched = ReminderScheduler(
            reminders_path=p, voice_service=voice,
            notify_via_osascript=False, speak_reminders=True,
        )
        sched.tick()
        voice.text_to_speech.assert_called_once()
        voice.play_audio.assert_called_once()


def test_invalid_json_does_not_crash():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "reminders.json"
        p.write_text("{ not json")
        sched = ReminderScheduler(reminders_path=p, voice_service=None,
                                  notify_via_osascript=False, speak_reminders=False)
        assert sched.tick() == 0
