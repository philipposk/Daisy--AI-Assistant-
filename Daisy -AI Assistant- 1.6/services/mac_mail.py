"""macOS Mail bridge via AppleScript (1.2; hardened in 1.6).

Provides: read recent messages, search, send, create draft.
No pip deps — pure subprocess / osascript.

1.6: every interpolated value goes through `_escape` (backslash first, then
quotes — order matters), including recipient addresses; osascript calls get
a timeout so a Mail permission dialog can't hang the server thread.
"""
from __future__ import annotations

import subprocess
from typing import Optional

OSASCRIPT_TIMEOUT = 30  # seconds; Mail can hang on permission/account dialogs


def _run_osascript(script: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=OSASCRIPT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 1, "", f"osascript timed out after {OSASCRIPT_TIMEOUT}s (permission dialog open?)"
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _escape(value: str) -> str:
    """Escape a value for an AppleScript double-quoted string.

    Backslash must be escaped before quotes, otherwise a literal `\\` in the
    input turns the following escaped quote back into a string terminator.
    Newlines are legal inside AppleScript strings only as `\\n` escapes.
    """
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def list_recent_messages(count: int = 10, mailbox: str = "INBOX") -> list[dict]:
    """Return the most recent <count> messages from <mailbox>."""
    count = max(1, min(int(count), 100))
    script = f'''
tell application "Mail"
    set acct to first account
    set mb to mailbox "{_escape(mailbox)}" of acct
    set msgs to messages of mb
    set total to count of msgs
    set lim to {count}
    if lim > total then set lim to total
    set output to ""
    repeat with i from 1 to lim
        set m to item i of msgs
        set output to output & subject of m & "|" & sender of m & "|" & (date received of m as string) & "|" & (read status of m as string) & "||"
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
        items.append({
            "subject": parts[0] if len(parts) > 0 else "",
            "from": parts[1] if len(parts) > 1 else "",
            "date": parts[2] if len(parts) > 2 else "",
            "read": parts[3].lower() == "true" if len(parts) > 3 else False,
        })
    return items


def search_messages(query: str, count: int = 10) -> list[dict]:
    """Search Mail for messages matching query (subject / sender)."""
    # AppleScript Mail search is limited; we filter subject/sender client-side
    script = f'''
tell application "Mail"
    set output to ""
    set acct to first account
    repeat with mb in every mailbox of acct
        try
            set msgs to (every message of mb whose subject contains "{_escape(query)}")
            repeat with m in msgs
                set output to output & subject of m & "|" & sender of m & "|" & (date received of m as string) & "||"
            end repeat
        end try
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
        if not chunk or len(items) >= count:
            continue
        parts = chunk.split("|")
        items.append({
            "subject": parts[0] if len(parts) > 0 else "",
            "from": parts[1] if len(parts) > 1 else "",
            "date": parts[2] if len(parts) > 2 else "",
        })
    return items


# ---------------------------------------------------------------------------
# Send / Draft
# ---------------------------------------------------------------------------

def send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> dict:
    """
    Send an email immediately via Mail.app.
    Returns {"ok": bool, "error": str|None}
    """
    cc_clause = (
        f'make new to recipient at end of cc recipients of new_msg with properties {{address:"{_escape(cc)}"}}'
        if cc else ""
    )

    script = f'''
tell application "Mail"
    set new_msg to make new outgoing message with properties {{subject:"{_escape(subject)}", content:"{_escape(body)}", visible:false}}
    tell new_msg
        make new to recipient at end of to recipients with properties {{address:"{_escape(to)}"}}
        {cc_clause}
    end tell
    send new_msg
end tell
'''
    rc, _, err = _run_osascript(script)
    if rc != 0:
        return {"ok": False, "error": err or "AppleScript error"}
    return {"ok": True, "error": None}


def create_draft(
    to: str,
    subject: str,
    body: str,
) -> dict:
    """
    Create a draft in Mail.app (visible compose window).
    Returns {"ok": bool, "error": str|None}
    """
    script = f'''
tell application "Mail"
    set new_msg to make new outgoing message with properties {{subject:"{_escape(subject)}", content:"{_escape(body)}", visible:true}}
    tell new_msg
        make new to recipient at end of to recipients with properties {{address:"{_escape(to)}"}}
    end tell
    activate
end tell
'''
    rc, _, err = _run_osascript(script)
    if rc != 0:
        return {"ok": False, "error": err or "AppleScript error"}
    return {"ok": True, "error": None}
