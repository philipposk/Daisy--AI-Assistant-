# Start Daisy 1.6

The short version:

```bash
cd "Daisy -AI Assistant- 1.6"
python3 daisy_app.py
```

That starts the backend on port **5188** and opens the app window (pywebview
if installed, otherwise your default browser at http://localhost:5188/).

## Other ways to run her

| Command | What it does |
|---|---|
| `python3 daisy_app.py --no-ui` | Backend only (use the browser yourself) |
| `python3 daisy_menubar.py` | Menu-bar icon with status + quick actions |
| `python3 tools/launchd_setup.py install` | Auto-start at login, restart on crash |
| `python3 daisy.py --text "make a note about X"` | One-shot CLI turn, no server |
| `python3 daisy.py` | CLI voice loop |

## First run checklist

1. `./setup.sh` once (installs dependencies, writes default config).
2. Add an API key — gear icon in the UI, or:
   `python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"`
3. Grant Microphone permission when macOS asks.

Stop Daisy with Ctrl+C (foreground) or
`python3 tools/launchd_setup.py uninstall` (launchd).
