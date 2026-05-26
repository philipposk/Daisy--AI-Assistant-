#!/usr/bin/env python3
"""
Daisy menu-bar tray icon (1.0).

Run alongside `daisy_app.py`. Shows a flower glyph in the macOS menu bar
with quick actions:

- Status (Listening / Speaking / Idle)
- Open Daisy …  (opens http://localhost:PORT/ in browser)
- Permissions … (opens System Settings if anything is missing)
- Quit Daisy

Requires `rumps` (`pip install rumps`). On non-macOS hosts it prints a
helpful message and exits.

Usage:
    python3 daisy_menubar.py              # connect to default :5188
    python3 daisy_menubar.py --port 7777
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import threading
import time
import urllib.request


def _try_rumps():
    try:
        import rumps  # type: ignore
        return rumps
    except ImportError:
        return None


def _open_browser(url: str) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["open", url], check=False)
    else:
        import webbrowser
        webbrowser.open(url)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=5188)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    rumps = _try_rumps()
    if rumps is None:
        print("rumps not installed. `pip install rumps` (macOS only).", file=sys.stderr)
        sys.exit(2)

    class DaisyApp(rumps.App):
        def __init__(self):
            # Use a flower-ish glyph in the title; can be replaced by an icon path.
            super().__init__("✿ Daisy", quit_button=None)
            self.menu = [
                "Open Daisy…",
                None,
                "Status: checking…",
                None,
                "Permissions…",
                None,
                "Quit Daisy",
            ]
            # Background poll so the Status line stays fresh.
            t = threading.Thread(target=self._poll, daemon=True)
            t.start()

        # ---------- menu items ----------

        @rumps.clicked("Open Daisy…")
        def on_open(self, _):
            _open_browser(base_url + "/")

        @rumps.clicked("Permissions…")
        def on_perms(self, _):
            # Hit the backend for a permissions report; pop a window if missing.
            try:
                with urllib.request.urlopen(base_url + "/api/permissions", timeout=2) as r:
                    import json as _json
                    report = _json.loads(r.read().decode())
            except Exception as e:
                rumps.alert("Daisy", f"Permission check failed: {e}")
                return
            missing = [k for k, v in report.items() if not v]
            if not missing:
                rumps.notification("Daisy", "Permissions", "All granted ✓")
                return
            choice = rumps.alert(
                "Daisy permissions",
                "Missing: " + ", ".join(missing) + ".\nOpen System Settings?",
                ok="Open Settings", cancel="Cancel",
            )
            if choice == 1 and missing:
                # Open the first missing pane via the same backend helper.
                try:
                    urllib.request.urlopen(
                        base_url + f"/api/permissions/open?kind={missing[0]}", timeout=2,
                    ).read()
                except Exception:
                    pass

        @rumps.clicked("Quit Daisy")
        def on_quit(self, _):
            rumps.quit_application()

        # ---------- background status poll ----------

        def _poll(self):
            while True:
                try:
                    with urllib.request.urlopen(base_url + "/api/state", timeout=1) as r:
                        import json as _json
                        s = _json.loads(r.read().decode())
                    provs = " → ".join(s.get("providers") or ["?"])
                    self.menu["Status: checking…"].title = f"Status: v{s.get('version','?')}  {provs}"
                except Exception:
                    self.menu["Status: checking…"].title = "Status: backend offline"
                time.sleep(3)

    DaisyApp().run()


if __name__ == "__main__":
    main()
