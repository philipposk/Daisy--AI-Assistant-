#!/usr/bin/env python3
"""
Daisy launchd setup tool (1.5).

Generates and installs a launchd plist so Daisy starts automatically on login.

Usage:
    python3 tools/launchd_setup.py install    # write plist + load agent
    python3 tools/launchd_setup.py uninstall  # unload + remove plist
    python3 tools/launchd_setup.py status     # show current state

The plist starts daisy_app.py with --no-ui --port 5188 and restarts it
if it crashes (KeepAlive = true with a 10-second throttle).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

LABEL = "com.daisy.assistant"
DEFAULT_PORT = 5188

PLIST_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{daisy_app}</string>
        <string>--no-ui</string>
        <string>--port</string>
        <string>{port}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{work_dir}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>ThrottleInterval</key>
    <integer>10</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{log_dir}/daisy.log</string>

    <key>StandardErrorPath</key>
    <string>{log_dir}/daisy-error.log</string>
</dict>
</plist>
"""


def _plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _log_dir() -> Path:
    d = Path.home() / ".daisy" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_plist(port: int = DEFAULT_PORT) -> str:
    here = Path(__file__).resolve().parent.parent  # project root
    python = sys.executable
    daisy_app = str(here / "daisy_app.py")
    return PLIST_TEMPLATE.format(
        label=LABEL,
        python=python,
        daisy_app=daisy_app,
        port=port,
        work_dir=str(here),
        log_dir=str(_log_dir()),
    )


def _gui_domain() -> str:
    return f"gui/{os.getuid()}"


def _bootstrap(dest: Path) -> subprocess.CompletedProcess:
    """Load the agent. `launchctl bootstrap` is the modern (macOS 11+) call;
    fall back to the deprecated `load` for very old systems."""
    result = subprocess.run(
        ["launchctl", "bootstrap", _gui_domain(), str(dest)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        result = subprocess.run(
            ["launchctl", "load", str(dest)], capture_output=True, text=True
        )
    return result


def _bootout(dest: Path) -> None:
    """Unload the agent (ignore 'not loaded' errors)."""
    r = subprocess.run(
        ["launchctl", "bootout", f"{_gui_domain()}/{LABEL}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        subprocess.run(["launchctl", "unload", str(dest)], capture_output=True)


def install(port: int = DEFAULT_PORT) -> None:
    """Write plist and load the launch agent."""
    plist_content = generate_plist(port)
    dest = _plist_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(plist_content)
    print(f"✅ Plist written to: {dest}")

    # Unload first in case it was already loaded
    _bootout(dest)

    result = _bootstrap(dest)
    if result.returncode != 0:
        print(f"⚠️  launchctl load failed: {result.stderr.strip()}")
        print("   You may need to re-run after granting Full Disk Access.")
    else:
        print(f"✅ Daisy launch agent loaded. It will start on next login.")
        print(f"   Listening on http://localhost:{port}/")


def uninstall() -> None:
    """Unload and remove the plist."""
    dest = _plist_path()
    if dest.exists():
        _bootout(dest)
        dest.unlink()
        print(f"✅ Launch agent removed: {dest}")
    else:
        print("ℹ️  No launch agent installed.")


def status() -> None:
    """Print current launchctl status for the Daisy agent."""
    result = subprocess.run(
        ["launchctl", "list", LABEL],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ℹ️  Daisy launch agent not loaded (label: {LABEL})")
    else:
        print(f"✅ Daisy launch agent is loaded:\n{result.stdout}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    if cmd == "install":
        install(port)
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "status":
        status()
    elif cmd == "generate":
        print(generate_plist(port))
    else:
        print(__doc__)
        sys.exit(0)


if __name__ == "__main__":
    main()
