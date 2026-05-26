"""
Lightweight MCP client (0.8).

Daisy's MCPToolCallAction goes through this client. We keep two long-lived
subprocesses (desktop_automation, computer_use) and talk JSON-RPC over stdio.

We deliberately do NOT pull in the full `mcp` Python SDK as a required dep —
this client speaks the wire protocol directly so 0.8 still runs on a fresh
machine without `pip install mcp`. If a user installs `mcp`, future versions
can swap in its richer client.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils import get_logger

logger = get_logger("mcp_client")


class MCPClient:
    """One stdio MCP server connection."""

    def __init__(self, name: str, command: List[str], cwd: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.cwd = cwd
        self.env = {**os.environ, **(env or {})}
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._next_id = 1
        self._initialized = False

    # ----------------- lifecycle -----------------

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            env=self.env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        logger.info(f"Started MCP server '{self.name}' pid={self._proc.pid}")
        self._initialize()

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            except Exception:
                pass
        self._proc = None
        self._initialized = False

    # ----------------- JSON-RPC -----------------

    def _send(self, payload: dict) -> dict:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError(f"MCP server '{self.name}' not running")
        line = json.dumps(payload) + "\n"
        with self._lock:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
            response_line = self._proc.stdout.readline()
            if not response_line:
                stderr = ""
                if self._proc.stderr is not None:
                    try:
                        stderr = self._proc.stderr.read(2048)
                    except Exception:
                        pass
                raise RuntimeError(f"MCP server '{self.name}' closed pipe. stderr: {stderr[:500]}")
        try:
            return json.loads(response_line)
        except json.JSONDecodeError:
            raise RuntimeError(f"MCP server '{self.name}' returned non-JSON: {response_line[:200]}")

    def _request(self, method: str, params: Optional[dict] = None) -> dict:
        req_id = self._next_id
        self._next_id += 1
        resp = self._send({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        })
        if "error" in resp:
            raise RuntimeError(f"MCP '{self.name}' error on {method}: {resp['error']}")
        return resp.get("result", {})

    def _initialize(self) -> None:
        try:
            self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "daisy", "version": "0.8"},
            })
            # MCP wants an initialized notification next, with no response
            with self._lock:
                if self._proc and self._proc.stdin:
                    self._proc.stdin.write(json.dumps({
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                    }) + "\n")
                    self._proc.stdin.flush()
            self._initialized = True
        except Exception as e:
            logger.warning(f"MCP '{self.name}' initialize failed: {e}")

    # ----------------- tools -----------------

    def list_tools(self) -> List[dict]:
        result = self._request("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: Optional[dict] = None,
                  timeout: Optional[int] = 60) -> dict:
        # Note: timeout is handled by the caller for now; full MCP cancellation
        # would require streaming awareness.
        deadline = time.monotonic() + (timeout or 60)
        try:
            return self._request("tools/call", {
                "name": name,
                "arguments": arguments or {},
            })
        finally:
            if time.monotonic() > deadline:
                logger.warning(f"MCP '{self.name}' tool '{name}' exceeded timeout {timeout}s")


class MCPRegistry:
    """Holds MCPClient handles by logical name. Lazy-starts."""

    LOGICAL_NAMES = ("desktop_automation", "computer_use")

    def __init__(self, config):
        self.config = config
        self._clients: Dict[str, MCPClient] = {}

    def get(self, logical_name: str) -> Optional[MCPClient]:
        if logical_name in self._clients:
            return self._clients[logical_name]

        command = None
        if logical_name == "desktop_automation":
            command = list(self.config.mcp.desktop_automation_command or [])
            # Sensible default if user hasn't configured: relative path inside the version folder.
            if not command:
                here = Path(__file__).resolve().parents[1]
                candidate = here / "mcp-desktop-automation" / "server.js"
                if candidate.exists():
                    command = ["node", str(candidate)]
        elif logical_name == "computer_use":
            command = list(self.config.mcp.computer_use_command or [])
            if not command:
                here = Path(__file__).resolve().parents[1]
                candidate = here / "mcp-computer-use" / "server.py"
                if candidate.exists():
                    command = ["python3", str(candidate)]

        if not command:
            return None

        client = MCPClient(name=logical_name, command=command)
        try:
            client.start()
        except FileNotFoundError as e:
            logger.warning(f"MCP server '{logical_name}' command not found: {e}")
            return None
        except Exception as e:
            logger.warning(f"MCP server '{logical_name}' failed to start: {e}")
            return None

        self._clients[logical_name] = client
        return client

    def close_all(self) -> None:
        for c in self._clients.values():
            c.stop()
        self._clients.clear()
