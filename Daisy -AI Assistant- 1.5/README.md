# Daisy 1.5 — Your Mac voice assistant

Daisy is a voice assistant that runs entirely on your Mac. You talk to her, she does
things for you — write notes, manage your calendar and email, remember facts about
you, and stay out of your way the rest of the time.

---

## What Daisy can do (plain English)

### Talk to her like a person
- **Say "Daisy"** — she wakes up and listens.
- **Just start talking** — she figures out when you're done; no button-mashing.
- **Interrupt her mid-sentence** — say "stop" and she stops talking.
- She filters out background-noise transcription junk so she doesn't act on
  garbled audio.

### Get things done with your voice
- **"Make a note about pasta recipes"** → markdown file in your notes folder.
- **"Add 'buy milk' to my tasks"** → goes in your tasks list AND your Mac's Reminders app.
- **"Remind me to drink water in 2 hours"** → real Mac notification + spoken reminder
  when the time comes.
- **"What's on my calendar today?"** → reads from Apple Calendar.
- **"Schedule a dentist appointment Tuesday 3 PM"** → creates the event in your calendar.
- **"Email Alice that I'll be late"** → drafts (or sends) email via Mail.app.
- **"Open Xcode and build the current project"** → controls apps on your desktop.

### She remembers you
- Tell her once: *"I prefer Python for scripting"* — she'll remember next time.
- She auto-summarizes old conversations so she keeps context without burning
  tokens on every reply.
- Search what she remembers: *"What do you know about my hobbies?"*

### Safety net built-in
- **"Undo that"** — actually undoes the last note/task/reminder/memory she created.
- **Audit log** — every action is logged; nothing happens silently.
- **Confirmation prompts** — for anything risky (running commands, deleting files),
  she asks first. If you're not there to answer, she does nothing.
- **API keys live in your Mac Keychain** — not in plain-text config files.

### Looks like a real Mac app
- **Web UI** at `http://localhost:5188/` — chat-style, streams her reply as she types.
- **Menu-bar icon** — quick status (Listening / Speaking / Idle) and one-click "open".
- **Auto-start on login** — one command, runs in the background forever.
- **Permission helper** — guides you through Mic / Accessibility / Screen-recording
  permissions if Daisy needs them.

---

## What's under the hood (short technical summary)

| Layer | How it works |
|-------|--------------|
| **Speech-to-text** | OpenAI Whisper API, or local `faster-whisper` via RealtimeSTT (streaming partials + Silero VAD) |
| **Wake word** | openWakeWord (offline, custom "daisy" model) OR Whisper-polling fallback |
| **LLM brain** | OpenAI / Anthropic / Groq / local Ollama — configurable provider chain with retry + fallback |
| **Action planning** | Pydantic-typed JSON output → dispatcher → safety check → executor |
| **Text-to-speech** | OpenAI TTS / Kokoro-ONNX (local) / Piper (local) / macOS `say` |
| **Persistence** | SQLite (tasks, conversation history, long-term memory) + JSON (reminders) + Markdown (notes, tasks) |
| **Backend** | FastAPI + uvicorn, port 5188, SSE for streaming, WebSocket for live transcript |
| **Frontend** | Single-page HTML (no build step), `EventSource` for typewriter streaming |
| **macOS integrations** | AppleScript via `osascript` — Calendar, Reminders, Mail, notifications |
| **MCP** | Daisy IS an MCP server (`listen`, `speak`, `notify`, `confirm`); also CONSUMES MCP servers (desktop-automation 12 tools, computer-use fallback) |
| **Secrets** | macOS Keychain via `security` CLI — no pip dep |
| **Tests** | 198/198 passing, mocked subprocess + filesystem; no real network in CI |

**Architecture:** Voice → Brain → Safety → Dispatch → Executor → TTS, plus a parallel
Memory + Summarizer feed into the Brain context window.

---

## Quick start

```bash
cd "Daisy -AI Assistant- 1.5"
./setup.sh

# Add your OpenAI key (recommended: Keychain, not env var):
python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"

# Start the backend + UI:
python3 daisy_app.py --port 5188 --no-ui
open http://localhost:5188/

# Or run with a native window:
python3 daisy_app.py --port 5188

# Or as a menu-bar app:
python3 daisy_menubar.py

# (Optional) auto-start on login:
python3 tools/launchd_setup.py install

# Run tests:
python3 tests/run_tests.py
```

---

## Project history

Daisy has shipped 11 releases (0.5 → 1.5). See [CHANGELOG.md](CHANGELOG.md) for
the full feature-by-feature breakdown, each entry written in plain English first
and then in technical detail.

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.10+
- ~200 MB disk for dependencies (more if you enable local Whisper / Kokoro)
- At least one of: OpenAI / Anthropic / Groq API key, OR a local Ollama server

---

## Privacy

- Everything except STT/LLM/TTS API calls runs locally.
- Switch to local-only mode by setting providers to `local_http` / `piper` / `whisper`.
- API keys go in your Mac Keychain by default.
- Audit log + memory DB live in `~/.daisy/` and never leave your machine.
