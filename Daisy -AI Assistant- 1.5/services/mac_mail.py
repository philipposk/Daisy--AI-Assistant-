"""macOS Mail bridge via AppleScript (1.2).

Provides: read recent messages, search, send, create draft.
No pip deps — pure subprocess / osascript.
"""
from __future__ import annotations

import subprocess
from typing import Optional


def _run_osascript(script: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def list_recent_messages(count: int = 10, mailbox: str = "INBOX") -> list[dict]:
    """Return the most recent <count> messages from <mailbox>."""
    script = f'''
tell application "Mail"
    set acct to first account
    set mb to mailbox "{mailbox}" of acct
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
            set msgs to (every message of mb whose subject contains "{query}")
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
    cc_clause = f'make new to recipient at end of cc recipients of new_msg with properties {{address:"{cc}"}}' if cc else ""
    # Escape quotes in body / subject
    safe_subject = subject.replace('"', '\\"')
    safe_body = body.replace('"', '\\"').replace("\n", "\\n")

    script = f'''
tell application "Mail"
    set new_msg to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:false}}
    tell new_msg
        make new to recipient at end of to recipients with properties {{address:"{to}"}}
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
    safe_subject = subject.replace('"', '\\"')
    safe_body = body.replace('"', '\\"').replace("\n", "\\n")

    script = f'''
tell application "Mail"
    set new_msg to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_body}", visible:true}}
    tell new_msg
        make new to recipient at end of to recipients with properties {{address:"{to}"}}
    end tell
    activate
end tell
'''
    rc, _, err = _run_osascript(script)
    if rc != 0:
        return {"ok": False, "error": err or "AppleScript error"}
    return {"ok": True, "error": None}
