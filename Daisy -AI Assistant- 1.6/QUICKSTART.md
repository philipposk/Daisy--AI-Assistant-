# Daisy 1.6 — Quick Start

Daisy is a voice assistant that runs entirely on your Mac. This guide gets her
running in about five minutes.

## 1. Requirements

- macOS (Calendar / Mail / Reminders integration is AppleScript-based)
- Python 3.10+
- Homebrew (for `portaudio`, needed by the microphone)
- An API key for at least one provider: OpenAI, Anthropic, Groq — or a local
  Ollama install for fully offline use.

## 2. Install

```bash
cd "Daisy -AI Assistant- 1.6"
./setup.sh
```

The setup script checks your Python version, installs dependencies, writes a
default config to `~/.daisy/config.yaml`, and snapshots your current
permission state.

## 3. Add an API key (stored in the macOS Keychain)

Either in the app: open Daisy → gear icon → API keys.

Or from the terminal:

```bash
python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"
```

Keys never live in plain-text files — they go into the same Keychain your Mac
uses for Wi-Fi passwords.

## 4. Run

```bash
python3 daisy_app.py            # opens the app window (or your browser)
# or:
python3 daisy_app.py --no-ui    # backend only, UI at http://localhost:5188/
```

Optional extras:

```bash
python3 daisy_menubar.py                       # menu-bar status icon
python3 tools/launchd_setup.py install         # auto-start on login
```

## 5. Talk to her

- Type in the web UI, or click the mic button, or say **"Daisy"** if the wake
  word is enabled in settings.
- "Make a note about pasta recipes"
- "Remind me in 2 hours to drink water"
- "What's on my calendar today?"
- "Undo that"

## Troubleshooting

- **Mic not working** → the UI shows a permission banner; click through to
  System Settings.
- **"backend offline" in the menu bar** → make sure `daisy_app.py` is running
  on port 5188 (the default).
- **Provider errors** → check the gear icon → API keys; Daisy falls back
  through the provider chain automatically.

For the full feature list see `README.md`; for release history see
`CHANGELOG.md`.
