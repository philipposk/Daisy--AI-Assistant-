#!/usr/bin/env python3
"""
Daisy MCP computer-use fallback server (0.8).

Exposes one tool:
  computer_use(goal: str, timeout_seconds: int = 120) -> text

Implementation strategy (no hard dependency on Agent-S):
- If `agent_s` is importable, drive it.
- Otherwise return a helpful "not installed" message so the LLM can
  pick a different path.

JSON-RPC over stdio — speaks the MCP 2024-11-05 protocol just enough to
work with `services/mcp_client.py`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import traceback
from typing import Any, Dict, Optional


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "daisy-computer-use"
SERVER_VERSION = "0.8"

TOOLS = [
    {
        "name": "computer_use",
        "description": (
            "Last-resort GUI driver. Given a natural-language `goal`, attempts "
            "to drive the macOS desktop via a vision-based agent. Use only when "
            "no native MCP tool can accomplish the goal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "What to achieve, in plain English."},
                "timeout_seconds": {"type": "integer", "default": 120},
            },
            "required": ["goal"],
        },
    }
]


def _write(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _result(id_: Any, result: Dict[str, Any]) -> None:
    _write({"jsonrpc": "2.0", "id": id_, "result": result})


def _error(id_: Any, code: int, message: str) -> None:
    _write({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _text_content(text: str, is_error: bool = False) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


# ------------------------- the actual tool -------------------------


def _run_agent_s(goal: str, timeout_seconds: int) -> Dict[str, Any]:
    """Try to call Agent-S via subprocess. Fall back to a friendly stub."""
    # Strategy 1: agent_s CLI on PATH
    cli = shutil.which("agent-s") or shutil.which("agents")
    if cli:
        try:
            proc = subprocess.run(
                [cli, "--goal", goal],
                capture_output=True, text=True, timeout=timeout_seconds,
            )
            output = (proc.stdout or "") + (("\nSTDERR:\n" + proc.stderr) if proc.stderr else "")
            return _text_content(output, is_error=proc.returncode != 0)
        except subprocess.TimeoutExpired:
            return _text_content(f"Agent-S timed out after {timeout_seconds}s.", is_error=True)
        except Exception as e:
            return _text_content(f"Agent-S subprocess failed: {e}", is_error=True)

    # Strategy 2: importable as a library
    try:
        import agent_s  # type: ignore  # noqa: F401
    except ImportError:
        return _text_content(
            "Agent-S not installed. Install with `pip install gui-agents` and re-run, "
            "or pick a more targeted MCP tool. "
            "Goal received: " + goal,
            is_error=True,
        )

    return _text_content(
        "Agent-S is importable but no integration glue is bundled in this Daisy build. "
        "Pick a more targeted MCP tool or implement the library bridge.",
        is_error=True,
    )


# ------------------------- JSON-RPC loop -------------------------


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
        # Notifications have no response
        return

    if method == "tools/list":
        _result(req_id, {"tools": TOOLS})
        return

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name != "computer_use":
            _error(req_id, -32601, f"Unknown tool: {name}")
            return
        goal = args.get("goal") or ""
        timeout = int(args.get("timeout_seconds") or 120)
        try:
            payload = _run_agent_s(goal, timeout)
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
            sys.stderr.write(f"bad json: {e}\n")
            sys.stderr.flush()
            continue
        try:
            _handle(req)
        except Exception:
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()


if __name__ == "__main__":
    main()
