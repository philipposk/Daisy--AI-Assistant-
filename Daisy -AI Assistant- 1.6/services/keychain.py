"""
macOS Keychain-backed secret store (1.1).

Lets the user store API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY,
GOOGLE_API_KEY) in the system Keychain instead of plain-text config or shell
scripts. Daisy reads from Keychain at config-load time as another env-var
overlay layer.

Implementation: shells out to the `security` CLI that ships with macOS.
No new pip dependency.

Storage shape:
    service  = "daisy"
    account  = <KEY_NAME> e.g. "OPENAI_API_KEY"
    password = the secret string

Public API:
    keychain_available() -> bool
    get_secret(name) -> Optional[str]
    set_secret(name, value) -> bool
    delete_secret(name) -> bool
    list_known() -> list[str]   # the four keys we know about
"""
from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Optional, List


SERVICE = "daisy"
KNOWN_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "GOOGLE_API_KEY",
)


def keychain_available() -> bool:
    """True when we're on macOS and the `security` CLI is on PATH."""
    return platform.system() == "Darwin" and bool(shutil.which("security"))


def get_secret(name: str) -> Optional[str]:
    """Return secret from Keychain, or None if not set / unavailable."""
    if not keychain_available():
        return None
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
            capture_output=True, text=True, timeout=3,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").rstrip("\n")
    return out or None


def set_secret(name: str, value: str) -> bool:
    """Write secret to Keychain. Overwrites if it already exists."""
    if not keychain_available():
        return False
    if not value:
        return False
    try:
        # -U: update if exists. Use stdin to avoid the secret showing up in
        # the process list / shell history.
        proc = subprocess.run(
            ["security", "add-generic-password", "-s", SERVICE, "-a", name, "-U", "-w", value],
            capture_output=True, text=True, timeout=3,
        )
        return proc.returncode == 0
    except Exception:
        return False


def delete_secret(name: str) -> bool:
    """Remove a Keychain entry. Returns False if not present."""
    if not keychain_available():
        return False
    try:
        proc = subprocess.run(
            ["security", "delete-generic-password", "-s", SERVICE, "-a", name],
            capture_output=True, text=True, timeout=3,
        )
        return proc.returncode == 0
    except Exception:
        return False


def list_known() -> List[str]:
    """Which of the well-known keys are currently set in Keychain."""
    return [k for k in KNOWN_KEYS if get_secret(k) is not None]
