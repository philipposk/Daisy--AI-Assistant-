#!/usr/bin/env python3
"""
Daisy-as-MCP-server (0.9).

Exposes Daisy's voice front-end as MCP tools so other agents (Claude Code,
OpenAI Agents, Pipecat, etc.) can use Daisy's mic + speaker:

  listen(timeout_seconds=10)            -> transcribed text
  speak(text)                           -> "ok"
  notify(message, voice=True)           -> "ok"
  confirm(prompt)                       -> "yes" | "no"

JSON-RPC over stdio. Uses the existing Daisy services (VoiceService,
ConfirmationProvider).

Run via:
    python3 daisy_mcp_server/server.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict

# Make Daisy importable when this script runs as a subprocess
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from config import load_config  # noqa: E402
from services import VoiceService  # noqa: E402
from services.confirmation import CLIConfirmation, VoiceConfirmation  # noqa: E402


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "daisy"
SERVER_VERSION = "0.9"

TOOLS = [
    {
        "name": "listen",
        "description": "Record the next user utterance and return its transcript.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "timeout_seconds": {"type": "integer", "default": 10},
            },
        },
    },
    {
        "name": "speak",
        "description": "Speak text aloud via Daisy's TTS voice.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "notify",
        "description": "Show a macOS desktop notification; optionally also speak it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "voice": {"type": "boolean", "default": True},
            },
            "required": ["message"],
        },
    },
    {
        "name": "confirm",
        "description": "Ask the user yes/no via voice. Returns 'yes' or 'no'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
            },
            "required": ["prompt"],
        },
    },
]


_voice: VoiceService = None  # lazy-initialized


def _get_voice() -> VoiceService:
    global _voice
    if _voice is None:
        _voice = VoiceService(load_config())
    return _voice


def _write(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _result(id_: Any, result: Dict[str, Any]) -> None:
    _write({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_: Any, code: int, message: str) -> None:
    _write({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _text_content(text: str, is_error: bool = False) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _escape_applescript(value: str) -> str:
    """Escape a value for safe interpolation inside an AppleScript string literal.

    Backslashes first (so we don't double-escape), then double quotes; newlines
    are flattened to spaces since notification text is single-line anyway.
    """
    value = str(value)
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return value


# ----------------- tool implementations -----------------


def _tool_listen(args: Dict[str, Any]) -> Dict[str, Any]:
    import speech_recognition as sr
    timeout = int(args.get("timeout_seconds") or 10)
    voice = _get_voice()
    recognizer = sr.Recognizer()
    try:
        microphone = sr.Microphone()
    except Exception as e:
        return _text_content(f"Microphone unavailable: {e}", is_error=True)
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
        except Exception as e:
            return _text_content(f"No speech captured: {e}", is_error=True)
    tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); tf.close()
    tmp = Path(tf.name)
    try:
        tmp.write_bytes(audio.get_wav_data())
        transcript = voice.transcribe_audio_file(tmp)
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    return _text_content(transcript.text or "")


def _tool_speak(args: Dict[str, Any]) -> Dict[str, Any]:
    text = args.get("text") or ""
    if not text.strip():
        return _text_content("empty text", is_error=True)
    voice = _get_voice()
    audio_path = voice.text_to_speech(text)
    voice.play_audio(audio_path, wait=True)
    try:
        audio_path.unlink()
    except Exception:
        pass
    return _text_content("ok")


def _tool_notify(args: Dict[str, Any]) -> Dict[str, Any]:
    msg = args.get("message") or ""
    with_voice = bool(args.get("voice", True))
    try:
        safe_msg = _escape_applescript(msg)
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_msg}" with title "Daisy"'],
            check=False, capture_output=True,
        )
    except FileNotFoundError:
        pass
    if with_voice:
        _tool_speak({"text": msg})
    return _text_content("ok")


def _tool_confirm(args: Dict[str, Any]) -> Dict[str, Any]:
    prompt = args.get("prompt") or "Confirm?"
    voice = _get_voice()
    try:
        provider = VoiceConfirmation(voice)
    except Exception:
        provider = CLIConfirmation()
    from schemas import AssistantAction
    # Minimal placeholder action; voice/CLI providers don't use it for prompting
    fake = AssistantAction(action_type="conversation", conversation=prompt)
    ok = provider.confirm(fake, prompt)
    return _text_content("yes" if ok else "no")


TOOL_IMPLS = {
    "listen": _tool_listen,
    "speak": _tool_speak,
    "notify": _tool_notify,
    "confirm": _tool_confirm,
}


# ----------------- JSON-RPC dispatcher -----------------


def _handle(request: Dict[str, Any]) -> None:
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
        return

    if method == "notifications/initialized":
        return

    if method == "tools/list":
        _result(req_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        impl = TOOL_IMPLS.get(name)
        if impl is None:
            _error(req_id, -32601, f"Unknown tool: {name}")
            return
        try:
            payload = impl(args)
        except Exception:
            payload = _text_content(traceback.format_exc(), is_error=True)
        _result(req_id, payload)
        return

    if req_id is not None:
        _error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"bad json: {e}\n"); sys.stderr.flush()
            continue
        try:
            _handle(req)
        except Exception:
            sys.stderr.write(traceback.format_exc()); sys.stderr.flush()


if __name__ == "__main__":
    main()
