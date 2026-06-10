"""Tests for mac_calendar service (1.2) — mocked osascript."""
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import mac_calendar


def _mock_run(returncode=0, stdout="", stderr=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_list_calendars_parses_output():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0, "Home, Work, Birthdays")):
        cals = mac_calendar.list_calendars()
    assert cals == ["Home", "Work", "Birthdays"]


def test_list_calendars_empty_on_failure():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(1, "", "error")):
        assert mac_calendar.list_calendars() == []


def test_list_events_today_parses_output():
    chunk = "Team meeting|Monday, May 26, 2026|Monday, May 26, 2026||"
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0, chunk)):
        events = mac_calendar.list_events_today()
    assert len(events) == 1
    assert events[0]["title"] == "Team meeting"


def test_create_event_ok():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0)):
        res = mac_calendar.create_event(
            title="Dentist", start_iso="2026-05-26T10:00:00", end_iso="2026-05-26T11:00:00"
        )
    assert res["ok"] is True
    assert res["error"] is None


def test_create_event_bad_iso():
    res = mac_calendar.create_event(
        title="Dentist", start_iso="not-a-date", end_iso="2026-05-26T11:00:00"
    )
    assert res["ok"] is False
    assert "Bad date format" in res["error"]


def test_create_event_applescript_fails():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(1, "", "Calendar not available")):
        res = mac_calendar.create_event(
            title="X", start_iso="2026-05-26T10:00:00", end_iso="2026-05-26T11:00:00"
        )
    assert res["ok"] is False


def test_list_reminders_parses_output():
    chunk = "Buy milk|Monday, May 26, 2026||Take out trash|||"
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0, chunk)):
        items = mac_calendar.list_reminders()
    assert len(items) == 2
    assert items[0]["title"] == "Buy milk"
    assert items[1]["title"] == "Take out trash"


def test_create_reminder_ok():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0)):
        res = mac_calendar.create_reminder(title="Feed cat")
    assert res["ok"] is True


def test_create_reminder_failure():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(1, "", "Reminders unavailable")):
        res = mac_calendar.create_reminder(title="Feed cat")
    assert res["ok"] is False


def test_create_reminder_with_due():
    with patch("services.mac_calendar.subprocess.run",
               return_value=_mock_run(0)) as mock_run:
        res = mac_calendar.create_reminder(title="Med", due_iso="2026-05-26T08:00:00")
    assert res["ok"] is True
    # Verify script contained the date
    script_arg = mock_run.call_args[0][0][2]
    assert "May" in script_arg or "due date" in script_arg
