## Daisy — AI Assistant

**Daisy** is a voice assistant that runs on your Mac. You talk to her, she does things for you — write notes, manage your calendar and email, remember facts about you, and stay out of your way the rest of the time.

This repo is a history of Daisy's evolution from a 50-line wake-word script (0.1) to a full Mac app with web UI, menu-bar tray, and auto-start (**1.5 — current stable**).

> **Important:** All API keys in this repo are intentionally **blank placeholders**.
> You must add your own keys locally before Daisy can talk to LLMs. In 1.1+, keys live in your Mac Keychain by default.

---

### Current version: 1.5

Open `Daisy -AI Assistant- 1.5/` for the latest version.

**What Daisy 1.5 can do:**

- **Say "Daisy"** — she wakes up, listens, replies. Interrupt her mid-sentence by saying "stop".
- **"Make a note about X"** → markdown file in your notes folder.
- **"Remind me in 2 hours to drink water"** → real Mac notification + spoken reminder.
- **"What's on my calendar?"** / **"Schedule a dentist Tuesday 3 PM"** → reads/writes Apple Calendar.
- **"Email Alice that I'll be late"** → drafts or sends via Mail.app.
- **"Open Xcode and build the project"** → drives apps on your desktop via MCP.
- **"I prefer Python"** → she remembers across sessions; auto-summarizes old conversations.
- **"Undo that"** → reverses the last note/task/reminder she created.
- Web UI at `localhost:5188`, menu-bar tray icon, audit log, settings API, auto-start on login.

**Quick start:**

```bash
cd "Daisy -AI Assistant- 1.5"
./setup.sh
python3 -c "from services.keychain import set_secret; set_secret('OPENAI_API_KEY', 'sk-...')"
python3 daisy_app.py --port 5188
open http://localhost:5188/
```

See `Daisy -AI Assistant- 1.5/README.md` and `CHANGELOG.md` for full details.

---

### Version history

Each `Daisy -AI Assistant- X.Y` folder is a self-contained snapshot.

| Version | What it added |
|---------|---------------|
| **0.1** | First minimal end-to-end Daisy: wake word, LLM call, basic desktop hooks |
| **0.2 / 0.25** | Reliability fixes, API quota handling, early voice support |
| **0.3** | Praiser sub-app, stronger TTS/voice pipelines |
| **0.4** | Robust voice stack, local Piper model flow, automation upgrades |
| **0.5** | "Assistant you can actually live with" — better docs, testing, MCP desktop automation, Xcode/Android build-retry |
| **0.6** | Clean rewrite: service architecture (Voice / Brain / Action / Safety), Pydantic schemas, SQLite, audit log, 41 tests |
| **0.7** | Bug-fix release: 22 fixes (shlex safety, JSON extractor, Piper TTS shell-out, dedup'd imports) |
| **0.8** | Wake-word loop, barge-in, confirmation prompts, reminder scheduler, MCP desktop + computer-use, Anthropic provider |
| **0.9** | RealtimeSTT, Kokoro TTS, Daisy-as-MCP-server, transcript hallucination filter, embedding tool router, FastAPI backend + frontend |
| **1.0** | SSE streaming UI, macOS permissions helper, menu-bar app (rumps) |
| **1.1** | macOS Keychain secrets; no more plain-text API keys |
| **1.2** | Calendar / Reminders / Mail bridges via AppleScript |
| **1.3** | Long-term memory store (SQLite), conversation summary compression |
| **1.4** | Undo stack, audit-log viewer, settings API |
| **1.5** | Stable release: launchd autostart, polished setup, health endpoint, full changelog |

### Architecture (1.5)

```
Voice → [STT] → Brain (LLM) → Safety check → Dispatcher → Executor → [TTS] → Voice
                    ↑                                            ↓
              [Memory + Summarizer]                        [Audit log + Undo stack]
```

- **STT**: OpenAI Whisper, faster-whisper (local), or `local_http`
- **LLM**: OpenAI / Anthropic / Groq / Ollama — provider chain with fallback
- **TTS**: OpenAI / Kokoro-ONNX (local) / Piper / macOS `say`
- **Persistence**: SQLite + JSON + Markdown, all in `~/.daisy/`
- **Backend**: FastAPI + uvicorn, port 5188
- **MCP**: Daisy IS an MCP server AND consumes MCP servers (desktop-automation, computer-use)

198/198 tests passing.

### Security & API Keys

- 1.1+: store keys in **macOS Keychain** via `services/keychain.py` (or env vars).
- Older versions: keys in `~/.daisy/config.json` — **never commit them**.
- If you commit a real key by accident: revoke it in the provider dashboard immediately, then rewrite history with `git filter-repo`.

### Requirements

- macOS (Apple Silicon or Intel)
- Python 3.10+
- ~200 MB disk for deps (more if you enable local Whisper / Kokoro)
- At least one of: OpenAI / Anthropic / Groq API key, OR a local Ollama server

### License

MIT — see `LICENSE`.
