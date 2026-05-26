"""macOS Calendar + Reminders bridge via AppleScript (1.2).

No pip deps — pure subprocess / osascript.
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_osascript(script: str) -> tuple[int, str, str]:
    """Run an AppleScript and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _available() -> bool:
    """Return True if we can talk to Calendar.app at all."""
    rc, _, _ = _run_osascript('tell application "Calendar" to get name of calendars')
    return rc == 0


# ---------------------------------------------------------------------------
# Calendar events
# ---------------------------------------------------------------------------

def list_calendars() -> list[str]:
    """Return list of calendar names."""
    rc, out, _ = _run_osascript(
        'tell application "Calendar" to get name of calendars'
    )
    if rc != 0 or not out:
        return []
    # AppleScript returns comma-separated list
    return [c.strip() for c in out.split(",") if c.strip()]


def list_events_today(calendar_name: Optional[str] = None) -> list[dict]:
    """Return events for today (optionally filtered to one calendar)."""
    today = datetime.now().strftime("%B %d, %Y")
    if calendar_name:
        script = f'''
tell application "Calendar"
    set cal to first calendar whose name is "{calendar_name}"
    set today_start to current date
    set time of today_start to 0
    set today_end to today_start + 86399
    set evt_list to (every event of cal whose start date >= today_start and start date <= today_end)
    set output to ""
    repeat with e in evt_list
        set output to output & summary of e & "|" & (start date of e as string) & "|" & (end date of e as string) & "||"
    end repeat
    return output
end tell
'''
    else:
        script = '''
tell application "Calendar"
    set today_start to current date
    set time of today_start to 0
    set today_end to today_start + 86399
    set output to ""
    repeat with cal in calendars
        set evt_list to (every event of cal whose start date >= today_start and start date <= today_end)
        repeat with e in evt_list
            set output to output & summary of e & "|" & (start date of e as string) & "|" & (end date of e as string) & "||"
        end repeat
    end repeat
    return output
end tell
'''
    rc, out, _ = _run_osascript(script)
    if rc != 0 or not out:
        return []
    events = []
    for chunk in out.split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        title = parts[0].strip()
        if not title:
            continue
        if len(parts) >= 3:
            events.append({
                "title": title,
                "start": parts[1].strip(),
                "end": parts[2].strip(),
            })
    return events


def create_event(
    title: str,
    start_iso: str,
    end_iso: str,
    calendar_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Create a calendar event.
    start_iso / end_iso: ISO 8601 strings, e.g. "2026-05-26T15:00:00"
    Returns {"ok": bool, "error": str|None}
    """
    try:
        start_dt = datetime.fromisoformat(start_iso)
        end_dt = datetime.fromisoformat(end_iso)
    except ValueError as exc:
        return {"ok": False, "error": f"Bad date format: {exc}"}

    # AppleScript date literal: "Monday, May 26, 2026 at 3:00:00 PM"
    def _fmt(dt: datetime) -> str:
        return dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")

    cal_clause = (
        f'set cal to first calendar whose name is "{calendar_name}"'
        if calendar_name else
        "set cal to first calendar"
    )
    notes_clause = f'set description of new_event to "{notes}"' if notes else ""

    script = f'''
tell application "Calendar"
    {cal_clause}
    set new_event to make new event at end of events of cal with properties {{summary:"{title}", start date:date "{_fmt(start_dt)}", end date:date "{_fmt(end_dt)}"}}
    {notes_clause}
    reload calendars
end tell
'''
    rc, _, err = _run_osascript(script)
    if rc != 0:
        return {"ok": False, "error": err or "AppleScript error"}
    return {"ok": True, "error": None}


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------

def list_reminder_lists() -> list[str]:
    """Return reminder list names."""
    rc, out, _ = _run_osascript(
        'tell application "Reminders" to get name of lists'
    )
    if rc != 0 or not out:
        return []
    return [r.strip() for r in out.split(",") if r.strip()]


def list_reminders(list_name: Optional[str] = None) -> list[dict]:
    """Return incomplete reminders (optionally filtered by list)."""
    if list_name:
        script = f'''
tell application "Reminders"
    set lst to first list whose name is "{list_name}"
    set rem_list to (every reminder of lst whose completed is false)
    set output to ""
    repeat with r in rem_list
        set d to ""
        try
            set d to (due date of r) as string
        end try
        set output to output & name of r & "|" & d & "||"
    end repeat
    return output
end tell
'''
    else:
        script = '''
tell application "Reminders"
    set output to ""
    repeat with lst in lists
        set rem_list to (every reminder of lst whose completed is false)
        repeat with r in rem_list
            set d to ""
            try
                set d to (due date of r) as string
            end try
            set output to output & name of r & "|" & d & "||"
        end repeat
    end repeat
    return output
end tell
'''
    rc, out, _ = _run_osascript(script)
    if rc != 0 or not out:
        return []
    items = []
    for chunk in out.split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        title = parts[0].strip()
        if not title:          # skip empty-title artifacts from trailing separators
            continue
        items.append({
            "title": title,
            "due": parts[1].strip() if len(parts) > 1 else "",
        })
    return items


def create_reminder(
    title: str,
    due_iso: Optional[str] = None,
    list_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Create a Reminders item.
    due_iso: optional ISO 8601 string
    Returns {"ok": bool, "error": str|None}
    """
    list_clause = (
        f'set lst to first list whose name is "{list_name}"'
        if list_name else
        "set lst to default list"
    )

    due_clause = ""
    if due_iso:
        try:
            due_dt = datetime.fromisoformat(due_iso)
            due_str = due_dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")
            due_clause = f'set due date of new_rem to date "{due_str}"'
        except ValueError:
            pass

    notes_clause = f'set body of new_rem to "{notes}"' if notes else ""

    script = f'''
tell application "Reminders"
    {list_clause}
    set new_rem to make new reminder at end of reminders of lst with properties {{name:"{title}"}}
    {due_clause}
    {notes_clause}
end tell
'''
    rc, _, err = _run_osascript(script)
    if rc != 0:
        return {"ok": False, "error": err or "AppleScript error"}
    return {"ok": True, "error": None}
