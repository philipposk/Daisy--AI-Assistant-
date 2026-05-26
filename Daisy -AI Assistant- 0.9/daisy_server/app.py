"""
Daisy HTTP / WebSocket backend (0.9).

This is the bridge between the Cursor-style frontend (Daisy.html) and the
Python DaisyPipeline. It exposes:

- GET  /                      → serve `frontend/Daisy.html`
- GET  /static/<file>         → static assets next to the html
- GET  /api/state             → status + recent tasks
- POST /api/turn              → run a single text turn (input → response + action results)
- POST /api/listen            → record from mic, transcribe, treat as turn input
- GET  /api/tasks             → list tasks
- POST /api/tasks/<id>/done   → mark task complete
- POST /api/reminders         → CRUD-light over reminders.json
- WS   /api/stream            → streaming partial transcript + intent + action events

The server uses a single shared DaisyPipeline instance.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Make Daisy importable
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
import sys
sys.path.insert(0, str(ROOT))

from daisy import DaisyPipeline  # noqa: E402
from utils import get_logger  # noqa: E402

logger = get_logger("daisy_server")


# ----------------- App state -----------------


class TurnRequest(BaseModel):
    text: str
    auto_approve: bool = False  # let trusted clients skip confirmation prompts


class TurnResponse(BaseModel):
    response: str
    actions: List[Dict[str, Any]] = []
    transcript: Optional[str] = None


_pipeline: Optional[DaisyPipeline] = None
_pipeline_lock = threading.Lock()


def get_pipeline() -> DaisyPipeline:
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                _pipeline = DaisyPipeline()
    return _pipeline


# ----------------- App factory -----------------


def create_app() -> FastAPI:
    app = FastAPI(title="Daisy", version="0.9")

    frontend_dir = ROOT / "frontend"
    html_path = frontend_dir / "Daisy.html"

    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    def index():
        if html_path.exists():
            return FileResponse(str(html_path))
        return HTMLResponse(
            "<h1>Daisy 0.9 backend up.</h1><p>frontend/Daisy.html missing.</p>",
            status_code=200,
        )

    @app.get("/api/state")
    def api_state():
        p = get_pipeline()
        return {
            "version": "0.9",
            "providers": p.brain_service._build_provider_chain(),
            "wake_word_enabled": p.config.wake_word.enabled,
            "reminder_enabled": p.config.reminder.enabled,
            "confirmation_mode": p.config.confirmation.mode,
        }

    @app.post("/api/turn", response_model=TurnResponse)
    def api_turn(req: TurnRequest):
        if not req.text.strip():
            raise HTTPException(400, "empty text")
        p = get_pipeline()
        # Auto-approve is wired by temporarily swapping the provider for trusted clients.
        original_provider = p.dispatcher.confirmation_provider
        if req.auto_approve:
            from services.confirmation import AutoApproveConfirmation
            p.dispatcher.confirmation_provider = AutoApproveConfirmation()
        try:
            resp = p.process_text(req.text)
        finally:
            p.dispatcher.confirmation_provider = original_provider
        return TurnResponse(response=resp, transcript=req.text, actions=[])

    @app.get("/api/tasks")
    def api_tasks():
        p = get_pipeline()
        return p.persistence.get_tasks(limit=200)

    @app.post("/api/tasks/{task_id}/done")
    def api_task_done(task_id: int):
        p = get_pipeline()
        ok = p.persistence.complete_task(task_id)
        if not ok:
            raise HTTPException(404, "task not found")
        return {"ok": True}

    @app.get("/api/reminders")
    def api_reminders():
        p = get_pipeline()
        path = Path(p.config.paths.reminders_file).expanduser()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text() or "[]")
        except Exception:
            return []

    @app.post("/api/listen")
    def api_listen(timeout_seconds: int = 8):
        """Record from mic, transcribe, run a turn. Returns same shape as /api/turn."""
        import speech_recognition as sr
        p = get_pipeline()
        recognizer = sr.Recognizer()
        try:
            microphone = sr.Microphone()
        except Exception as e:
            raise HTTPException(500, f"Microphone unavailable: {e}")
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = recognizer.listen(source, timeout=timeout_seconds,
                                          phrase_time_limit=timeout_seconds)
            except Exception as e:
                raise HTTPException(504, f"No speech captured: {e}")
        tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); tf.close()
        tmp = Path(tf.name)
        try:
            tmp.write_bytes(audio.get_wav_data())
            transcript = p.voice_service.transcribe_audio_file(tmp)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass
        if not transcript.text.strip():
            return TurnResponse(response="(silence)", transcript=transcript.text, actions=[])
        resp = p.process_text(transcript.text)
        return TurnResponse(response=resp, transcript=transcript.text, actions=[])

    @app.websocket("/api/stream")
    async def stream(ws: WebSocket):
        """
        Send {type:'turn', text:'...'} to run a turn. Receive a series of frames:
          {type:'transcript', text:'...'}
          {type:'response', text:'...'}
          {type:'done'}
        For now this is one-shot per message (no token streaming yet). Hooks for
        live partials are in place — wire RealtimeSTT here in a future revision.
        """
        await ws.accept()
        try:
            p = get_pipeline()
            while True:
                msg_raw = await ws.receive_text()
                try:
                    msg = json.loads(msg_raw)
                except json.JSONDecodeError:
                    await ws.send_text(json.dumps({"type": "error", "error": "bad json"}))
                    continue
                if msg.get("type") == "turn":
                    text = msg.get("text") or ""
                    await ws.send_text(json.dumps({"type": "transcript", "text": text}))
                    loop = asyncio.get_event_loop()
                    resp = await loop.run_in_executor(None, p.process_text, text)
                    await ws.send_text(json.dumps({"type": "response", "text": resp}))
                    await ws.send_text(json.dumps({"type": "done"}))
                else:
                    await ws.send_text(json.dumps({"type": "error", "error": "unknown type"}))
        except WebSocketDisconnect:
            return

    return app


# Module-level app for `uvicorn daisy_server.app:app`
app = create_app()
