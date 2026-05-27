# Daisy 1.0 — Real Mac app feel

Daisy now feels like a real Mac app instead of a script. Small icon in your menu bar shows whether she's listening, speaking, or idle. Her replies type out word-by-word like a chat app instead of arriving in one chunk. When she needs microphone or screen-recording permission, she walks you straight to the right pane in System Settings.

## New in 1.0

- **SSE streaming** — `GET /api/turn-stream?text=` with events `transcript` → `partial`×N → `done`; frontend uses `EventSource` for typewriter effect
- **`services/permissions.py`** — checks Mic (PyAudio probe), Accessibility (osascript), Screen Recording (Quartz `CGPreflightScreenCaptureAccess`)
- **API**: `GET /api/permissions`, `GET /api/permissions/open?kind=mic|accessibility|screen` (deep-links System Settings)
- **`daisy_menubar.py`** — rumps tray icon, polls `/api/state` every 3s; menu: Status / Open / Permissions / Quit

## Tests

117/117 passing.

## Quick start

```bash
./setup.sh
python3 daisy_app.py --port 5188 --no-ui   # backend headless
python3 daisy_menubar.py                    # menu-bar app
open http://localhost:5188/
```
