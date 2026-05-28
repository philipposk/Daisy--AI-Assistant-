# Daisy — Your Talking Assistant

Daisy is a voice assistant that lives on your Mac. You talk to her out loud and she does things for you: takes notes, sets reminders, checks your calendar, drafts emails, and remembers facts about you so you don't have to repeat yourself. Think of her as a hands-free helper that stays quiet until you say her name.

She's built for anyone who'd rather speak a quick request than stop and type it. The rest of the time she stays out of your way in the background.

## What it does
- Wakes up when you say "Daisy", listens, and replies out loud (say "stop" to cut her off)
- Takes notes for you when you ask ("make a note about...")
- Sets reminders that pop up and speak to you ("remind me in 2 hours to drink water")
- Reads and updates your Apple Calendar ("what's on my calendar?", "schedule a dentist Tuesday at 3pm")
- Drafts and sends emails through the Mail app
- Remembers your preferences between conversations
- Lets you take back the last thing she did ("undo that")
- Has a simple window in your web browser and a small icon in the top menu bar

## Status
Working desktop app for Mac. The folder holds the full history of Daisy from a tiny first version to the current stable release (1.5). To use it you add your own AI account key — none are included.

---
### For developers
Python 3.10+, macOS only. Each `Daisy -AI Assistant- X.Y` folder is a self-contained snapshot; **1.5** is current stable (198/198 tests passing). Architecture is a pipeline: Voice → speech-to-text → LLM "brain" → safety check → dispatcher → executor → text-to-speech, with a SQLite memory store, audit log, and undo stack. Backend is FastAPI + uvicorn on port 5188. Pluggable providers for speech-to-text (Whisper / faster-whisper / local), LLM (OpenAI / Anthropic / Groq / Ollama with fallback chain), and text-to-speech (OpenAI / Kokoro / Piper / macOS `say`). Daisy is both an MCP server and an MCP client (desktop automation, computer-use). API keys live in the macOS Keychain (1.1+) — never committed. Quick start:

```bash
cd "Daisy -AI Assistant- 1.5"
./setup.sh
python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"
python3 daisy_app.py --port 5188
open http://localhost:5188/
```

See `Daisy -AI Assistant- 1.5/README.md` and `CHANGELOG.md` for full details. License: MIT.
