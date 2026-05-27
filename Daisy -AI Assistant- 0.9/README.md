# Daisy 0.9 — Modern OSS stack

Daisy gets a real web UI (no command-line needed), can listen with better quality voice models that run locally on your Mac, and can be used as a voice front-end by other AI tools (like Claude Code). She stops hallucinating words from background noise.

## New in 0.9

- **`RealtimeSTT`** integration — WebRTC + Silero VAD + faster-whisper; streaming partials ("I heard…")
- **Kokoro-ONNX** TTS — Apache-2.0, 82M params, local CPU (~1-2s TTFB); Piper fallback
- **openWakeWord** backend for custom "daisy" wake word
- **`daisy_mcp_server/server.py`** — Daisy IS an MCP server: `listen` / `speak` / `notify` / `confirm` tools. Claude Code etc. can use Daisy as voice front-end
- **`services/transcript_filter.py`** — drops Whisper hallucination phantoms ("thanks for watching", "subtitles by…")
- **`services/tool_router.py`** — keyword router for MCP tools; embedding mode via sentence-transformers (optional)
- **`daisy_server/`** — FastAPI + uvicorn backend (port 5188)
  - `GET /api/state`, `POST /api/turn`, `POST /api/listen`, `GET /api/tasks`, `WS /api/stream`
- **`frontend/Daisy.html`** — single-file SPA, no build step
- **`daisy_app.py`** — PyWebView native shell + `--no-ui --port N` headless mode

## Quick start

```bash
./setup.sh
python3 daisy_app.py --port 5188 --no-ui
open http://localhost:5188/
```

## Tests

All passing.
