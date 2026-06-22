"""
First-run macOS permission check (1.0).

Checks whether Daisy has the OS-level grants it needs:
- Microphone
- Accessibility (to drive other apps via MCP desktop automation)
- Screen Recording (for screenshot tools)

We don't try to *force* a grant — macOS owns that dialog. We:
1. Detect current status via `tccutil` / `osascript` checks.
2. If any missing, open System Settings to the right pane via `x-apple.systempreferences:`.
3. Return a structured report so the frontend can show a friendly banner.

Public API:
    report = check_permissions()      # dict {mic: bool, accessibility: bool, screen: bool}
    open_settings(kind="mic")          # opens the relevant System Settings pane

This is best-effort. On non-macOS hosts, all checks return True (no-op).
"""
from __future__ import annotations

import platform
import subprocess
from typing import Dict


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def check_microphone() -> bool:
    """
    Best-effort microphone-access check.

    macOS doesn't expose a clean "do I have mic permission?" API to scripts,
    but we can probe via `tccutil reset` (no — destructive) or by trying to
    open the mic with PyAudio and catching the OS error. We do the latter
    lazily to avoid spinning up audio for no reason.
    """
    if not _is_macos():
        return True
    try:
        import pyaudio  # type: ignore
    except ImportError:
        # Without PyAudio we can't probe; assume OK (the actual call will
        # raise the system permission dialog when needed).
        return True
    try:
        pa = pyaudio.PyAudio()
        try:
            stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000,
                             input=True, frames_per_buffer=512)
            stream.stop_stream()
            stream.close()
            return True
        finally:
            pa.terminate()
    except Exception:
        return False


def check_accessibility() -> bool:
    """
    Uses AppleScript to ask System Events if it can do anything. If TCC
    hasn't granted accessibility to this app, the query fails with a
    specific error code.
    """
    if not _is_macos():
        return True
    try:
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True, text=True, timeout=4,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def check_screen_recording() -> bool:
    """
    macOS exposes `CGPreflightScreenCaptureAccess()` via PyObjC. If PyObjC is
    not installed we fall back to "True" so we don't gate on an optional dep.
    """
    if not _is_macos():
        return True
    try:
        from Quartz import CGPreflightScreenCaptureAccess  # type: ignore
        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return True  # best-effort


def check_permissions() -> Dict[str, bool]:
    """Run all checks and return a status dict."""
    return {
        "microphone": check_microphone(),
        "accessibility": check_accessibility(),
        "screen_recording": check_screen_recording(),
    }


# Maps logical kind → the System Settings deep-link pane URL.
_PANE = {
    "mic": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "screen": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
}


def open_settings(kind: str = "mic") -> bool:
    """Open the relevant System Settings privacy pane."""
    if not _is_macos():
        return False
    url = _PANE.get(kind)
    if not url:
        return False
    try:
        subprocess.run(["open", url], check=False)
        return True
    except Exception:
        return False


def summary_line(report: Dict[str, bool]) -> str:
    """Human-friendly one-line summary for log / banner."""
    missing = [k for k, v in report.items() if not v]
    if not missing:
        return "All permissions granted."
    return "Missing: " + ", ".join(missing)
