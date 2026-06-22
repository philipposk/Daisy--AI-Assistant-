"""
Smoke test for the Daisy-as-MCP server (0.9).

Spawns daisy_mcp_server/server.py as a subprocess, issues an initialize
+ tools/list, verifies the four tools are exposed.

This is a smoke test — no real microphone interaction.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
SERVER = HERE / "daisy_mcp_server" / "server.py"


def _rpc(proc, payload):
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()
    return json.loads(proc.stdout.readline())


def test_initialize_and_list_tools():
    if not SERVER.exists():
        return  # nothing to test
    env = os.environ.copy()
    # Force a tmp config so the server doesn't touch ~/.daisy
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="daisy-mcp-"))
    cfg = tmp / "config.yaml"
    cfg.write_text("paths:\n  notes_directory: " + str(tmp / "notes") + "\n")

    proc = subprocess.Popen(
        [sys.executable, str(SERVER)],
        cwd=str(HERE),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, env=env,
    )
    try:
        init = _rpc(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2024-11-05",
                                      "capabilities": {}, "clientInfo": {"name": "test"}}})
        assert "result" in init
        assert init["result"]["serverInfo"]["name"] == "daisy"

        # tools/list
        tl = _rpc(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        assert "result" in tl
        names = {t["name"] for t in tl["result"]["tools"]}
        assert {"listen", "speak", "notify", "confirm"}.issubset(names)
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
