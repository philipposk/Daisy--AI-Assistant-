#!/usr/bin/env python3
"""
Daisy 0.9 native shell.

Spawns the FastAPI backend in a thread and opens a native window pointed at
the served frontend. Three runtimes, picked in order of preference:

1. pywebview (`pip install pywebview`) — proper native window with Daisy
   menubar items, no browser chrome.
2. PyQt6 + QWebEngineView — only used if PyQt is already on the path.
3. system default browser — fallback that always works.

Usage:
    python3 daisy_app.py            # opens the UI
    python3 daisy_app.py --no-ui    # just runs the server (headless)
    python3 daisy_app.py --port 8765
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import uvicorn  # noqa: E402

from daisy_server.app import app  # noqa: E402


def _serve(host: str, port: int) -> None:
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _open_window(url: str) -> None:
    # 1. pywebview
    try:
        import webview  # type: ignore
        webview.create_window("Daisy", url, width=1180, height=760)
        webview.start()
        return
    except ImportError:
        pass

    # 2. system browser fallback
    webbrowser.open(url)
    print(f"Daisy 0.9 UI opened in your default browser: {url}")
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-ui", action="store_true", help="Run backend only, no window")
    args = ap.parse_args()

    server_thread = threading.Thread(
        target=_serve, args=(args.host, args.port), daemon=True, name="daisy-uvicorn",
    )
    server_thread.start()

    if not _wait_for_port(args.port, timeout=10):
        print(f"[daisy_app] backend did not come up on :{args.port}; exiting", file=sys.stderr)
        sys.exit(1)

    url = f"http://{args.host}:{args.port}/"

    if args.no_ui:
        print(f"Daisy 0.9 backend running at {url} (no window).")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    _open_window(url)


if __name__ == "__main__":
    main()
