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

import atexit
import json
import os
import queue
import subprocess
import threading
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
        # Drain stderr in the background so the child never blocks on a full
        # pipe; lines are surfaced in our log instead of silently buffering.
        if self._proc.stderr is not None:
            threading.Thread(
                target=self._drain_stderr,
                args=(self._proc,),
                daemon=True,
                name=f"mcp-{self.name}-stderr",
            ).start()
        self._initialize()

    def _drain_stderr(self, proc: subprocess.Popen) -> None:
        try:
            for line in proc.stderr:  # type: ignore[union-attr]
                line = line.rstrip()
                if line:
                    logger.debug(f"MCP '{self.name}' stderr: {line}")
        except Exception:
            pass

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    try:
                        self._proc.wait(timeout=1.0)
                    except Exception:
                        pass
            except Exception:
                pass
        self._proc = None
        self._initialized = False

    # ----------------- JSON-RPC -----------------

    DEFAULT_TIMEOUT = 30.0

    def _send(self, payload: dict, timeout: Optional[float] = None) -> dict:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError(f"MCP server '{self.name}' not running")
        timeout = timeout if timeout and timeout > 0 else self.DEFAULT_TIMEOUT
        line = json.dumps(payload) + "\n"
        with self._lock:
            self._proc.stdin.write(line)
            self._proc.stdin.flush()
            # Read the response in a worker thread so a stuck server can't
            # hang the caller forever.
            result_q: "queue.Queue" = queue.Queue()
            stdout = self._proc.stdout

            def _read_line() -> None:
                try:
                    result_q.put(("line", stdout.readline()))
                except Exception as exc:
                    result_q.put(("error", exc))

            reader = threading.Thread(
                target=_read_line, daemon=True, name=f"mcp-{self.name}-read",
            )
            reader.start()
            try:
                kind, value = result_q.get(timeout=timeout)
            except queue.Empty:
                raise RuntimeError(
                    f"MCP server '{self.name}' timed out after {timeout}s waiting for a response"
                )
            if kind == "error":
                raise RuntimeError(f"MCP server '{self.name}' read failed: {value}")
            response_line = value
            if not response_line:
                raise RuntimeError(
                    f"MCP server '{self.name}' closed pipe (see log for its stderr output)"
                )
        try:
            return json.loads(response_line)
        except json.JSONDecodeError:
            raise RuntimeError(f"MCP server '{self.name}' returned non-JSON: {response_line[:200]}")

    def _request(self, method: str, params: Optional[dict] = None,
                 timeout: Optional[float] = None) -> dict:
        req_id = self._next_id
        self._next_id += 1
        resp = self._send({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }, timeout=timeout)
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
        return self._request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        }, timeout=float(timeout or 60))


# Module-level bookkeeping so child MCP processes are always cleaned up on
# interpreter exit, no matter how many registries get created.
_registries: List["MCPRegistry"] = []
_atexit_registered = False


def _close_all_registries() -> None:
    for registry in list(_registries):
        try:
            registry.close_all()
        except Exception:
            pass


class MCPRegistry:
    """Holds MCPClient handles by logical name. Lazy-starts."""

    LOGICAL_NAMES = ("desktop_automation", "computer_use")

    def __init__(self, config):
        self.config = config
        self._clients: Dict[str, MCPClient] = {}
        global _atexit_registered
        _registries.append(self)
        if not _atexit_registered:
            atexit.register(_close_all_registries)
            _atexit_registered = True

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
