"""1.6 hardening regression tests.

Covers the audit findings fixed in 1.6: confirmation enforcement, AppleScript
escaping, safety-checker bypasses, persistent undo, note path confinement,
and the shared reminders store.
"""
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# AppleScript escaping
# ---------------------------------------------------------------------------

def test_calendar_escape_quotes_and_backslashes():
    from services.mac_calendar import _escape
    assert _escape('say "hi"') == 'say \\"hi\\"'
    # Backslash escaped BEFORE quote — order matters.
    assert _escape('back\\slash') == 'back\\\\slash'
    assert '\n' not in _escape('line1\nline2')


def test_mail_escape_recipient_address():
    from services.mac_mail import _escape
    evil = 'a@b.com" & (do shell script "id") & "'
    escaped = _escape(evil)
    assert '\\"' in escaped
    # No bare double-quote can remain that would terminate the literal.
    assert '"' not in escaped.replace('\\"', '')


def test_applescript_date_is_numeric():
    from services.mac_calendar import _applescript_date
    from datetime import datetime
    script = _applescript_date("d", datetime(2026, 6, 1, 15, 30, 0))
    assert "set year of d to 2026" in script
    assert "set month of d to 6" in script
    assert "set hours of d to 15" in script
    # No locale-dependent month/weekday names
    assert "June" not in script and "Monday" not in script


# ---------------------------------------------------------------------------
# Safety checker hardening
# ---------------------------------------------------------------------------

def _make_checker(**safety_overrides):
    from actions.safety import SafetyChecker
    from config import load_config
    cfg = load_config()
    for k, v in safety_overrides.items():
        setattr(cfg.safety, k, v)
    return SafetyChecker(cfg)


def test_safety_blocks_nested_shell():
    checker = _make_checker(block_network_commands=True, whitelisted_commands=[])
    ok, reason = checker._check_command('bash -c "curl http://evil"')
    assert not ok
    assert "shell" in reason.lower() or "bash" in reason.lower()


def test_safety_blocks_command_substitution():
    checker = _make_checker(block_network_commands=True, whitelisted_commands=[])
    ok, reason = checker._check_command('echo $(curl http://evil)')
    assert not ok


def test_safety_blocks_rm_rf_variants():
    checker = _make_checker(whitelisted_commands=[])
    for cmd in ("rm -fr /tmp/x", "rm --recursive --force /tmp/x",
                "rm -Rf /tmp/x", "rm -r -f /tmp/x"):
        ok, reason = checker._check_command(cmd)
        assert not ok, f"should block: {cmd}"


def test_safety_still_allows_plain_ls():
    checker = _make_checker(whitelisted_commands=[])
    ok, _ = checker._check_command("ls -la")
    assert ok


# ---------------------------------------------------------------------------
# Dispatcher confirmation semantics
# ---------------------------------------------------------------------------

def test_force_confirmation_cannot_be_skipped_without_auto_approve():
    """Intent-level requires_confirmation must ADD a prompt requirement."""
    from actions.dispatcher import ActionDispatcher
    from config import load_config
    from schemas import AssistantAction

    cfg = load_config()
    dispatcher = ActionDispatcher(cfg, audit_logger=None, confirmation_provider=None)
    action = AssistantAction(
        action_type="create_note",
        create_note={"title": "t", "content": "c"},
    )
    # force_confirmation + no provider → must fail closed, not execute.
    results = dispatcher.dispatch_actions(
        [action], auto_approve=False, force_confirmation=True
    )
    assert len(results) == 1
    assert not results[0].success
    assert "confirmation" in (results[0].error or "").lower()


def test_per_call_confirmation_provider_override():
    """A per-call provider must be used without mutating the dispatcher."""
    from actions.dispatcher import ActionDispatcher
    from config import load_config
    from schemas import AssistantAction

    class ApproveAll:
        def confirm(self, action, prompt):
            return True

    cfg = load_config()
    with tempfile.TemporaryDirectory() as td:
        cfg.paths.notes_directory = td
        dispatcher = ActionDispatcher(cfg, audit_logger=None, confirmation_provider=None)
        action = AssistantAction(
            action_type="create_note",
            create_note={"title": "ok", "content": "c"},
        )
        results = dispatcher.dispatch_actions(
            [action], force_confirmation=True, confirmation_provider=ApproveAll()
        )
        assert results[0].success
        # Shared instance untouched
        assert dispatcher.confirmation_provider is None


# ---------------------------------------------------------------------------
# Note path confinement
# ---------------------------------------------------------------------------

def test_note_path_cannot_escape_notes_dir():
    from services.action_service import ActionService
    from config import load_config
    from schemas import AssistantAction

    with tempfile.TemporaryDirectory() as td:
        cfg = load_config()
        cfg.paths.notes_directory = str(Path(td) / "notes")
        cfg.paths.database_path = str(Path(td) / "daisy.db")
        cfg.paths.tasks_file = str(Path(td) / "tasks.md")
        cfg.paths.reminders_file = str(Path(td) / "reminders.json")
        svc = ActionService(cfg)

        action = AssistantAction(
            action_type="create_note",
            create_note={
                "title": "evil",
                "content": "x",
                "path": str(Path(td) / "outside" / "escape.md"),
            },
        )
        result = svc.execute_action(action)
        assert result.success
        written = Path(result.metadata["path"])
        # Must be inside the notes dir, not the requested outside path.
        assert str(written).startswith(str(Path(cfg.paths.notes_directory).resolve()))
        assert not (Path(td) / "outside" / "escape.md").exists()


# ---------------------------------------------------------------------------
# Persistent undo stack
# ---------------------------------------------------------------------------

def test_undo_stack_survives_restart():
    from services.undo_stack import UndoStack, UndoEntry

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "undo.json"
        s1 = UndoStack(persist_path=path)
        s1.push(UndoEntry(action_type="create_task", description="t1",
                          metadata={"title": "t1"}))
        s1.push(UndoEntry(action_type="create_note", description="n1",
                          metadata={"path": "/tmp/n1.md"}))
        assert path.exists()

        # Simulated restart: a fresh stack loads from disk.
        s2 = UndoStack(persist_path=path)
        assert len(s2) == 2
        top = s2.pop()
        assert top.action_type == "create_note"
        assert top.metadata["path"] == "/tmp/n1.md"

        # Pop persisted too.
        s3 = UndoStack(persist_path=path)
        assert len(s3) == 1


def test_undo_reminder_removes_only_matching_created_at():
    from services.undo_stack import UndoManager, UndoEntry
    from config import load_config

    with tempfile.TemporaryDirectory() as td:
        cfg = load_config()
        cfg.paths.reminders_file = str(Path(td) / "reminders.json")
        reminders = [
            {"message": "drink water", "created_at": "2026-01-01T10:00:00"},
            {"message": "drink water", "created_at": "2026-01-01T11:00:00"},
        ]
        Path(cfg.paths.reminders_file).write_text(json.dumps(reminders))

        mgr = UndoManager(cfg)
        entry = UndoEntry(
            action_type="create_reminder",
            description="r",
            metadata={"message": "drink water", "created_at": "2026-01-01T10:00:00"},
        )
        res = mgr.execute(entry)
        assert res["ok"]
        remaining = json.loads(Path(cfg.paths.reminders_file).read_text())
        assert len(remaining) == 1
        assert remaining[0]["created_at"] == "2026-01-01T11:00:00"


# ---------------------------------------------------------------------------
# Shared reminders store
# ---------------------------------------------------------------------------

def test_reminders_store_concurrent_writes_dont_lose_entries():
    from services.reminders_store import reminders_lock, read_reminders, write_reminders

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "reminders.json"
        write_reminders(path, [])

        def add(n):
            for i in range(20):
                with reminders_lock():
                    data = read_reminders(path)
                    data.append({"message": f"r-{n}-{i}"})
                    write_reminders(path, data)

        threads = [threading.Thread(target=add, args=(n,)) for n in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(read_reminders(path)) == 80


# ---------------------------------------------------------------------------
# Server: origin guard + settings patch route exist
# ---------------------------------------------------------------------------

def test_origin_guard_logic():
    from daisy_server.app import _origin_allowed
    assert _origin_allowed(None)                       # curl / same-origin
    assert _origin_allowed("http://localhost:5188")
    assert _origin_allowed("http://127.0.0.1:5188")
    assert not _origin_allowed("https://evil.example")
    assert not _origin_allowed("null")


def test_turn_stream_rejects_foreign_origin():
    from fastapi.testclient import TestClient
    from daisy_server.app import app

    client = TestClient(app)
    r = client.get(
        "/api/turn-stream",
        params={"text": "hi"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# 1.6 feature endpoints
# ---------------------------------------------------------------------------

def test_memory_export_route_not_shadowed():
    """/api/memory/export must not be captured by /api/memory/{topic}."""
    from fastapi.testclient import TestClient
    from daisy_server.app import app

    client = TestClient(app)
    r = client.get("/api/memory/export")
    assert r.status_code == 200
    assert "markdown" in r.headers["content-type"]


def test_memory_import_roundtrip():
    from fastapi.testclient import TestClient
    from daisy_server.app import app

    client = TestClient(app)
    md = (
        "---\n"
        "id: test-import-topic-16\n"
        "type: memory\n"
        "tags: [daisy]\n"
        "created: 2026-06-01\n"
        "---\n\n"
        "# test-import-topic-16\n\n"
        "imported content here\n"
    )
    r = client.post("/api/memory/import", json={"markdown": md})
    assert r.status_code == 200
    assert r.json()["imported"] == 1

    r2 = client.get("/api/memory/test-import-topic-16")
    assert r2.status_code == 200
    assert "imported content" in r2.json()["content"]

    # cleanup
    client.delete("/api/memory/test-import-topic-16")


def test_settings_patch_rejects_empty_and_accepts_known():
    from fastapi.testclient import TestClient
    from daisy_server.app import app

    client = TestClient(app)
    r = client.patch("/api/settings", json={})
    assert r.status_code == 400

    # Patch a harmless field; live config object should reflect it.
    r2 = client.patch("/api/settings", json={"tts_voice": "nova"})
    assert r2.status_code == 200
    assert r2.json()["applied"] == {"tts_voice": "nova"}


# ---------------------------------------------------------------------------
# 1.6 circuit breaker + cost tracking
# ---------------------------------------------------------------------------

def test_circuit_breaker_opens_after_threshold():
    from services.provider_health import CircuitBreaker

    cb = CircuitBreaker(threshold=3, cooldown=60.0)
    assert cb.allow("openai")
    cb.record_failure("openai")
    cb.record_failure("openai")
    assert cb.allow("openai")          # still under threshold
    cb.record_failure("openai")        # third failure → open
    assert not cb.allow("openai")
    # A different provider is unaffected.
    assert cb.allow("groq")
    # Success resets.
    cb.record_success("openai")
    assert cb.allow("openai")


def test_circuit_breaker_half_open_after_cooldown():
    from services.provider_health import CircuitBreaker

    cb = CircuitBreaker(threshold=1, cooldown=0.0)  # cooldown 0 → instantly half-open
    cb.record_failure("openai")
    # opened, but cooldown 0 means a trial is immediately allowed
    assert cb.allow("openai")


def test_cost_tracker_accumulates_and_persists():
    from services.provider_health import CostTracker

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "costs.json"
        t1 = CostTracker(persist_path=path)
        t1.record_call("openai")
        t1.record_call("openai")
        t1.record_call("groq")  # free → $0
        s = t1.summary()
        assert s["providers"]["openai"]["calls"] == 2
        assert s["providers"]["groq"]["estimated_usd"] == 0.0
        assert s["total_estimated_usd"] > 0

        # Reload from disk.
        t2 = CostTracker(persist_path=path)
        assert t2.summary()["providers"]["openai"]["calls"] == 2


def test_costs_and_provider_health_endpoints():
    from fastapi.testclient import TestClient
    from daisy_server.app import app

    client = TestClient(app)
    r = client.get("/api/costs")
    assert r.status_code == 200
    assert "total_estimated_usd" in r.json()

    r2 = client.get("/api/providers/health")
    assert r2.status_code == 200
    assert "chain" in r2.json()
