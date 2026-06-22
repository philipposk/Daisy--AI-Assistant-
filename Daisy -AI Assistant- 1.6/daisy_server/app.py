"""
Daisy HTTP / WebSocket backend (1.6).

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

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
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


# 1.2 — module-level payload models (must be at module scope for FastAPI body detection)

class _CalEventPayload(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    calendar_name: Optional[str] = None
    notes: Optional[str] = None


class _MacReminderPayload(BaseModel):
    title: str
    due_iso: Optional[str] = None
    list_name: Optional[str] = None
    notes: Optional[str] = None


class _SendEmailPayload(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    draft_only: bool = False


# 1.3 memory payloads
class _MemoryRememberPayload(BaseModel):
    topic: str
    content: str
    source: str = "explicit"


# 1.6 payloads (module scope — FastAPI body detection)
class _MemoryImportPayload(BaseModel):
    markdown: str


class _SettingsPatch(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    stt_provider: Optional[str] = None
    wake_word_enabled: Optional[bool] = None
    reminder_enabled: Optional[bool] = None
    confirmation_mode: Optional[str] = None


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


DAISY_VERSION = "1.6"

# Origins allowed to talk to the API from a browser context. Daisy binds to
# localhost, but ANY website the user visits can still fire requests at
# http://127.0.0.1:<port> — the browser sends them regardless of CORS (CORS
# only hides the response). Rejecting foreign Origins server-side closes that
# cross-site request hole.
_ALLOWED_ORIGIN_HOSTS = ("localhost", "127.0.0.1")


def _origin_allowed(origin: Optional[str]) -> bool:
    if not origin or origin == "null":
        # Same-origin requests and non-browser clients (curl, menubar) often
        # send no Origin header at all — those are fine.
        return origin != "null"
    try:
        from urllib.parse import urlparse
        host = urlparse(origin).hostname or ""
    except Exception:
        return False
    return host in _ALLOWED_ORIGIN_HOSTS


def create_app() -> FastAPI:
    app = FastAPI(title="Daisy", version=DAISY_VERSION)

    @app.middleware("http")
    async def reject_foreign_origins(request, call_next):
        if not _origin_allowed(request.headers.get("origin")):
            return JSONResponse(
                {"error": "cross-origin requests are not allowed"}, status_code=403
            )
        return await call_next(request)

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
            "version": DAISY_VERSION,
            "providers": p.brain_service._build_provider_chain(),
            "wake_word_enabled": p.config.wake_word.enabled,
            "reminder_enabled": p.config.reminder.enabled,
            "confirmation_mode": p.config.confirmation.mode,
        }

    # 1.1: macOS Keychain CRUD for API keys.
    class _KeyPayload(BaseModel):
        name: str
        value: str

    @app.get("/api/keychain")
    def api_keychain_list():
        from services.keychain import keychain_available, list_known, KNOWN_KEYS
        return {
            "available": keychain_available(),
            "known_keys": list(KNOWN_KEYS),
            "set_keys": list_known(),
        }

    @app.post("/api/keychain")
    def api_keychain_set(payload: _KeyPayload):
        from services.keychain import set_secret, KNOWN_KEYS, keychain_available
        if not keychain_available():
            raise HTTPException(503, "Keychain not available (macOS only)")
        if payload.name not in KNOWN_KEYS:
            raise HTTPException(400, f"unknown key name; choose from {list(KNOWN_KEYS)}")
        if not payload.value.strip():
            raise HTTPException(400, "empty value")
        ok = set_secret(payload.name, payload.value)
        if not ok:
            raise HTTPException(500, "keychain write failed")
        return {"ok": True, "name": payload.name}

    @app.delete("/api/keychain/{name}")
    def api_keychain_delete(name: str):
        from services.keychain import delete_secret, KNOWN_KEYS, keychain_available
        if not keychain_available():
            raise HTTPException(503, "Keychain not available")
        if name not in KNOWN_KEYS:
            raise HTTPException(400, "unknown key name")
        ok = delete_secret(name)
        return {"ok": ok, "name": name}

    # 1.0: permissions endpoints used by the menu-bar + frontend first-run banner
    @app.get("/api/permissions")
    def api_permissions():
        from services.permissions import check_permissions
        return check_permissions()

    @app.get("/api/permissions/open")
    def api_permissions_open(kind: str = Query("mic")):
        from services.permissions import open_settings
        ok = open_settings(kind)
        return {"ok": ok, "kind": kind}

    # 1.0: SSE streaming endpoint. Server pseudo-streams the response by
    # chunking on whitespace; replace with real LLM token streaming when the
    # brain service starts emitting partials.
    #
    # 1.6: `auto_approve` is no longer accepted here. EventSource forces this
    # to be a GET, and a GET with side effects must not also carry a
    # confirmation bypass — auto-approval is only available on POST /api/turn.
    @app.get("/api/turn-stream")
    def api_turn_stream(text: str = Query(...)):
        if not text.strip():
            raise HTTPException(400, "empty text")
        p = get_pipeline()

        def _gen():
            yield f"event: transcript\ndata: {json.dumps({'text': text})}\n\n"
            resp = p.process_text(text)
            # Pseudo-stream by word so the UI gets the typewriter effect.
            words = resp.split(" ")
            buf = ""
            for w in words:
                buf = (buf + " " + w).strip()
                yield f"event: partial\ndata: {json.dumps({'text': buf})}\n\n"
            yield f"event: done\ndata: {json.dumps({'text': resp})}\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")

    @app.post("/api/turn", response_model=TurnResponse)
    def api_turn(req: TurnRequest):
        if not req.text.strip():
            raise HTTPException(400, "empty text")
        p = get_pipeline()
        # 1.6: auto_approve flows through process_text as a per-call argument.
        # The old implementation swapped the shared dispatcher's confirmation
        # provider and restored it in `finally` — two overlapping requests
        # could interleave and leave the server permanently auto-approving.
        resp = p.process_text(req.text, auto_approve=req.auto_approve)
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
        timeout_seconds = max(1, min(int(timeout_seconds), 30))
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

    # ------------------------------------------------------------------
    # 1.2 — macOS Calendar / Reminders / Mail endpoints
    # ------------------------------------------------------------------

    @app.get("/api/calendar/events")
    def api_calendar_events(calendar: Optional[str] = None):
        """Return today's events (optionally filtered by calendar name)."""
        from services.mac_calendar import list_events_today
        events = list_events_today(calendar_name=calendar)
        return {"events": events}

    @app.get("/api/calendar/calendars")
    def api_calendar_list():
        from services.mac_calendar import list_calendars
        return {"calendars": list_calendars()}

    @app.post("/api/calendar/events")
    def api_calendar_create(payload: _CalEventPayload):
        from services.mac_calendar import create_event
        res = create_event(
            title=payload.title,
            start_iso=payload.start_iso,
            end_iso=payload.end_iso,
            calendar_name=payload.calendar_name,
            notes=payload.notes,
        )
        if not res["ok"]:
            raise HTTPException(500, res.get("error", "Failed to create event"))
        return {"ok": True}

    @app.get("/api/reminders/lists")
    def api_reminder_lists():
        from services.mac_calendar import list_reminder_lists
        return {"lists": list_reminder_lists()}

    @app.get("/api/mac-reminders")
    def api_mac_reminders(list_name: Optional[str] = None):
        from services.mac_calendar import list_reminders
        return {"reminders": list_reminders(list_name=list_name)}

    @app.post("/api/mac-reminders")
    def api_mac_reminder_create(payload: _MacReminderPayload):
        from services.mac_calendar import create_reminder
        res = create_reminder(
            title=payload.title,
            due_iso=payload.due_iso,
            list_name=payload.list_name,
            notes=payload.notes,
        )
        if not res["ok"]:
            raise HTTPException(500, res.get("error", "Failed to create reminder"))
        return {"ok": True}

    @app.get("/api/mail/messages")
    def api_mail_messages(count: int = 10, mailbox: str = "INBOX"):
        from services.mac_mail import list_recent_messages
        return {"messages": list_recent_messages(count=count, mailbox=mailbox)}

    @app.get("/api/mail/search")
    def api_mail_search(q: str, count: int = 10):
        from services.mac_mail import search_messages
        return {"messages": search_messages(query=q, count=count)}

    @app.post("/api/mail/send")
    def api_mail_send(payload: _SendEmailPayload):
        from services.mac_mail import send_email, create_draft
        if payload.draft_only:
            res = create_draft(to=payload.to, subject=payload.subject, body=payload.body)
        else:
            res = send_email(to=payload.to, subject=payload.subject, body=payload.body, cc=payload.cc)
        if not res["ok"]:
            raise HTTPException(500, res.get("error", "Mail operation failed"))
        return {"ok": True}

    # ------------------------------------------------------------------
    # 1.3 — Long-term memory endpoints
    # ------------------------------------------------------------------

    def _get_memory_store():
        """Get MemoryStore from pipeline or create a standalone one."""
        pipe = get_pipeline()
        if hasattr(pipe, "memory_store"):
            return pipe.memory_store
        from services.memory import MemoryStore
        from pathlib import Path as _Path
        db = _Path(pipe.config.paths.database_path).expanduser().parent / "memory.db"
        return MemoryStore(db)

    @app.get("/api/memory")
    def api_memory_list():
        """List all stored memories."""
        store = _get_memory_store()
        return {"memories": store.list_all()}

    @app.get("/api/memory/search")
    def api_memory_search(q: str, limit: int = 5):
        """Keyword search across memories."""
        store = _get_memory_store()
        return {"memories": store.search(q, limit=limit)}

    # 1.6: portable memory — export as markdown with YAML frontmatter
    # (SecondBrain vault format). MUST be declared before the /{topic} route
    # or FastAPI would match "export" as a topic name.
    @app.get("/api/memory/export")
    def api_memory_export():
        """Export all memories as a single markdown document."""
        store = _get_memory_store()
        memories = store.list_all()
        blocks = []
        for m in memories:
            topic = m.get("topic", "")
            content = m.get("content", "")
            created = m.get("created_at") or m.get("updated_at") or ""
            blocks.append(
                "---\n"
                f"id: {topic}\n"
                "type: memory\n"
                "tags: [daisy]\n"
                f"created: {created}\n"
                "---\n\n"
                f"# {topic}\n\n{content}\n"
            )
        body = "\n".join(blocks) if blocks else "# No memories yet\n"
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            body,
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=daisy-memories.md"},
        )

    @app.get("/api/memory/{topic}")
    def api_memory_recall(topic: str):
        """Retrieve a single memory by topic."""
        store = _get_memory_store()
        content = store.recall(topic)
        if content is None:
            raise HTTPException(404, f"No memory found for topic: {topic}")
        return {"topic": topic, "content": content}

    @app.post("/api/memory")
    def api_memory_remember(payload: _MemoryRememberPayload):
        """Store or update a memory."""
        store = _get_memory_store()
        store.remember(topic=payload.topic, content=payload.content, source=payload.source)
        return {"ok": True}

    @app.delete("/api/memory/{topic}")
    def api_memory_forget(topic: str):
        """Delete a memory."""
        store = _get_memory_store()
        found = store.forget(topic)
        if not found:
            raise HTTPException(404, f"No memory found for topic: {topic}")
        return {"ok": True}

    @app.post("/api/memory/import")
    def api_memory_import(payload: _MemoryImportPayload):
        """Import memories from the export format (id + body per block)."""
        import re
        store = _get_memory_store()
        imported = 0
        # Each block: frontmatter fence with an id, then "# title\n\ncontent"
        # up to the next fence (or end of document).
        pattern = re.compile(
            r"---\n(?P<front>.*?)\n---\n\s*#[^\n]*\n\n(?P<content>.*?)(?=\n---\n|\Z)",
            re.DOTALL,
        )
        for m in pattern.finditer(payload.markdown):
            id_match = re.search(r"^id:\s*(.+)$", m.group("front"), re.MULTILINE)
            if not id_match:
                continue
            topic = id_match.group(1).strip()
            content = m.group("content").strip()
            if topic and content:
                store.remember(topic=topic, content=content, source="import")
                imported += 1
        return {"ok": True, "imported": imported}

    # ------------------------------------------------------------------
    # 1.4 — Undo stack endpoints
    # ------------------------------------------------------------------

    @app.get("/api/undo")
    def api_undo_list():
        """Return the current undo stack (most recent last)."""
        pipe = get_pipeline()
        if not hasattr(pipe, "undo_stack"):
            return {"undo_stack": []}
        return {"undo_stack": pipe.undo_stack.list()}

    @app.post("/api/undo")
    def api_undo_execute():
        """Execute undo of the most recent reversible action."""
        pipe = get_pipeline()
        if not hasattr(pipe, "undo_stack") or not hasattr(pipe, "undo_manager"):
            raise HTTPException(503, "Undo not available")
        entry = pipe.undo_stack.pop()
        if entry is None:
            raise HTTPException(404, "Nothing to undo")
        result = pipe.undo_manager.execute(entry)
        if not result["ok"]:
            raise HTTPException(500, result.get("error", "Undo failed"))
        return result

    # ------------------------------------------------------------------
    # 1.4 — Audit log viewer endpoint
    # ------------------------------------------------------------------

    @app.get("/api/log")
    def api_log(lines: int = 50):
        """Return last N lines from the audit log as JSONL entries."""
        pipe = get_pipeline()
        log_path = Path(pipe.config.paths.audit_log).expanduser()
        if not log_path.exists():
            return {"entries": []}
        all_lines = log_path.read_text(errors="replace").splitlines()
        tail = all_lines[-lines:]
        entries = []
        for line in tail:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"raw": line})
        return {"entries": entries}

    # ------------------------------------------------------------------
    # 1.4 — Settings endpoints (read config + patch writable fields)
    # ------------------------------------------------------------------

    @app.get("/api/settings")
    def api_settings_get():
        """Return current config as a flat dict of user-editable settings."""
        pipe = get_pipeline()
        cfg = pipe.config
        return {
            "llm_provider": getattr(cfg.llm, "provider", "openai"),
            "llm_model": getattr(cfg.llm, "model", "gpt-4o-mini"),
            "tts_provider": getattr(cfg.tts, "provider", "openai"),
            "tts_voice": getattr(cfg.tts, "voice", "nova"),
            "stt_provider": getattr(cfg.stt, "provider", "openai"),
            "wake_word_enabled": getattr(cfg.wake_word, "enabled", False),
            "reminder_enabled": getattr(cfg.reminder, "enabled", True),
            "confirmation_mode": getattr(getattr(cfg, "confirmation", None), "mode", "cli"),
        }

    # 1.6: settings are finally writable. Whitelisted flat keys map onto the
    # nested config structure; the patch is merged into ~/.daisy/config.yaml
    # (or .json if PyYAML is missing) and applied to the live config so the
    # change takes effect without a restart where possible.
    _SETTINGS_MAP = {
        "llm_provider": ("llm", "provider"),
        "llm_model": ("llm", "model"),
        "tts_provider": ("tts", "provider"),
        "tts_voice": ("tts", "voice"),
        "stt_provider": ("stt", "provider"),
        "wake_word_enabled": ("wake_word", "enabled"),
        "reminder_enabled": ("reminder", "enabled"),
        "confirmation_mode": ("confirmation", "mode"),
    }

    @app.patch("/api/settings")
    def api_settings_patch(patch: _SettingsPatch):
        """Persist whitelisted settings to the user config file + live config."""
        changes = {k: v for k, v in patch.model_dump().items() if v is not None}
        if not changes:
            raise HTTPException(400, "no recognized settings in patch")

        config_path = Path.home() / ".daisy" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing user config (file may be yaml or absent)
        existing: Dict[str, Any] = {}
        if config_path.exists():
            try:
                import yaml
                existing = yaml.safe_load(config_path.read_text()) or {}
            except Exception:
                existing = {}

        pipe = get_pipeline()
        applied = {}
        for flat_key, value in changes.items():
            section, attr = _SETTINGS_MAP[flat_key]
            existing.setdefault(section, {})[attr] = value
            # Best-effort live application
            section_obj = getattr(pipe.config, section, None)
            if section_obj is not None and hasattr(section_obj, attr):
                setattr(section_obj, attr, value)
            applied[flat_key] = value

        try:
            import yaml
            config_path.write_text(yaml.safe_dump(existing, sort_keys=False))
        except ImportError:
            config_path = config_path.with_suffix(".json")
            config_path.write_text(json.dumps(existing, indent=2))

        return {"ok": True, "applied": applied, "config_path": str(config_path),
                "note": "Some settings (providers, wake word) need a restart to fully apply."}

    # ------------------------------------------------------------------
    # 1.5 — Health check + version history
    # ------------------------------------------------------------------

    @app.get("/api/health")
    def api_health():
        """Lightweight health check for launchd watchdog / uptime monitors."""
        import time
        return {"status": "ok", "version": DAISY_VERSION, "ts": time.time()}

    # 1.6: provider circuit-breaker status + estimated spend
    @app.get("/api/providers/health")
    def api_providers_health():
        p = get_pipeline()
        breaker = getattr(p.brain_service, "circuit_breaker", None)
        return {
            "chain": p.brain_service._build_provider_chain(),
            "breakers": breaker.status() if breaker else {},
        }

    @app.get("/api/costs")
    def api_costs():
        p = get_pipeline()
        tracker = getattr(p.brain_service, "cost_tracker", None)
        if tracker is None:
            return {"providers": {}, "total_estimated_usd": 0.0}
        return tracker.summary()

    @app.get("/api/version-history")
    def api_version_history():
        """Return the full release history of Daisy."""
        return {
            "versions": [
                {"version": "0.5", "summary": "Voice-first monolith, MCP desktop automation, Praiser, Xcode build-retry"},
                {"version": "0.6", "summary": "Clean rewrite: Pydantic schemas, service split (Voice/Brain/Action/Safety), SQLite, audit log"},
                {"version": "0.7", "summary": "Bug-fix release: 22 fixes across all services, shlex safety, JSON extractor, Piper TTS"},
                {"version": "0.8", "summary": "Wake word, barge-in, confirmation prompts, reminder scheduler, MCP desktop + computer-use, Anthropic provider"},
                {"version": "0.9", "summary": "RealtimeSTT, Kokoro TTS, Daisy-as-MCP-server, transcript filter, embedding tool router, FastAPI backend, frontend"},
                {"version": "1.0", "summary": "SSE streaming, macOS permissions UI, menu-bar tray icon (rumps)"},
                {"version": "1.1", "summary": "macOS Keychain secrets store, API key management endpoints"},
                {"version": "1.2", "summary": "Calendar, Reminders, Mail bridges via AppleScript"},
                {"version": "1.3", "summary": "Long-term memory store (SQLite), conversation summary compression"},
                {"version": "1.4", "summary": "Undo stack, audit log viewer, settings API"},
                {"version": "1.5", "summary": "Stable release: launchd autostart, setup.sh, health endpoint, CHANGELOG polish"},
                {"version": "1.6", "summary": "Hardening release: confirmation layer enforced per-action, AppleScript escaping, cross-origin guard, persistent undo, thread-safe turns"},
            ]
        }

    return app


# Module-level app for `uvicorn daisy_server.app:app`
app = create_app()
