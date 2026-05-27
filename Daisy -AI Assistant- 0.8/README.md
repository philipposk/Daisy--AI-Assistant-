# Daisy 0.8 — Real voice assistant

Daisy becomes a real voice assistant instead of a "press button, then talk" tool. She listens continuously for her name, lets you cut her off when she's talking too much, actually asks before doing risky things, and fires reminders on time. She can also drive other apps on your desktop (open Xcode, click buttons, take screenshots) and talk to Anthropic's Claude models, not just OpenAI.

## New in 0.8

- **`services/wake_word.py`** — openWakeWord (offline custom model) OR Whisper-poll fallback
- **`services/barge_in.py`** — VAD listener during TTS; speech detected → kill playback handle
- **`services/confirmation.py`** — `CLIConfirmationProvider`, `VoiceConfirmationProvider`, auto-approve/reject
- **`services/reminder_scheduler.py`** — background thread polls `reminders.json`, fires via `osascript display notification` + TTS; recurring reminders re-scheduled
- **`mcp-desktop-automation/server.js`** — Node MCP server, 12 tools (`take_screenshot`, `build_with_retry`, `detect_build_errors`, etc.) lifted from 0.5
- **`mcp-computer-use/server.py`** — Agent-S wrapper as last-resort GUI driver
- **Anthropic provider** in `brain_service.py` with prompt-caching support
- **Date injection** into system prompt (fixes "remind me tomorrow")
- **Conversation summary** when history > 20 messages
- **Fallback chain**: OpenAI → Anthropic → Groq → Ollama with exponential back-off

## New action type

- `mcp_tool_call` — `{server, tool, args}` dispatched to MCP registry

## Tests

All passing (0.7's 41 + new tests for each service).

## Quick start

```bash
./setup.sh
python3 daisy.py                                                   # voice loop with wake word
python3 daisy.py --input "remind me to drink water in 2 minutes"   # 2 min later → mac notification
node mcp-desktop-automation/server.js                              # MCP server
```
