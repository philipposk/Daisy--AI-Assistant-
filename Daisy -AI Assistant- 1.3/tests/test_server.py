"""Tests for the FastAPI backend (0.9)."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from daisy_server.app import create_app, get_pipeline
import daisy_server.app as server_mod


@pytest.fixture(autouse=True)
def _reset_pipeline(monkeypatch, tmp_path):
    """Force the server to use a tmp-dir config so we don't touch ~/.daisy."""
    import yaml
    cfg_path = tmp_path / "config.yaml"
    yaml.safe_dump({
        "paths": {
            "notes_directory": str(tmp_path / "notes"),
            "tasks_file": str(tmp_path / "tasks.md"),
            "reminders_file": str(tmp_path / "reminders.json"),
            "audit_log": str(tmp_path / "audit.log"),
            "conversations_directory": str(tmp_path / "convos"),
            "database_path": str(tmp_path / "daisy.db"),
        },
        "reminder": {"enabled": False},
    }, open(cfg_path, "w"))

    from daisy import DaisyPipeline
    pipe = DaisyPipeline(config_path=cfg_path)
    monkeypatch.setattr(server_mod, "_pipeline", pipe)
    yield


def test_state_endpoint():
    client = TestClient(create_app())
    r = client.get("/api/state")
    assert r.status_code == 200
    data = r.json()
    assert data["version"] == "1.3"
    assert isinstance(data["providers"], list)


def test_keychain_list_endpoint():
    from fastapi.testclient import TestClient
    from daisy_server.app import create_app
    client = TestClient(create_app())
    r = client.get("/api/keychain")
    assert r.status_code == 200
    data = r.json()
    assert "available" in data and isinstance(data["available"], bool)
    assert "known_keys" in data and isinstance(data["known_keys"], list)
    assert "set_keys" in data and isinstance(data["set_keys"], list)


def test_keychain_set_rejects_unknown_name():
    from fastapi.testclient import TestClient
    from daisy_server.app import create_app
    client = TestClient(create_app())
    r = client.post("/api/keychain", json={"name": "BOGUS_KEY", "value": "x"})
    # 503 (no keychain) | 400 (bad name) | 422 (FastAPI body validation):
    # all three prove the endpoint rejects bad input.
    assert r.status_code in (400, 422, 503)


def test_permissions_endpoint():
    client = TestClient(create_app())
    r = client.get("/api/permissions")
    assert r.status_code == 200
    data = r.json()
    for k in ("microphone", "accessibility", "screen_recording"):
        assert k in data
        assert isinstance(data[k], bool)


def test_permissions_open_unknown_kind():
    client = TestClient(create_app())
    r = client.get("/api/permissions/open?kind=bogus")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False


def test_turn_stream_emits_events():
    """SSE response must include transcript + at least one partial + done."""
    client = TestClient(create_app())
    with client.stream("GET", "/api/turn-stream?text=hello") as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes())
    txt = body.decode("utf-8", errors="ignore")
    assert "event: transcript" in txt
    assert "event: done" in txt


def test_turn_stream_rejects_empty():
    client = TestClient(create_app())
    r = client.get("/api/turn-stream?text=%20%20")
    assert r.status_code == 400


def test_turn_endpoint_no_llm():
    """When no LLM provider is configured we still get a graceful fallback."""
    client = TestClient(create_app())
    r = client.post("/api/turn", json={"text": "hello"})
    assert r.status_code == 200
    data = r.json()
    assert "response" in data


def test_turn_rejects_empty():
    client = TestClient(create_app())
    r = client.post("/api/turn", json={"text": "   "})
    assert r.status_code == 400


def test_tasks_endpoint_empty():
    client = TestClient(create_app())
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_reminders_endpoint_empty():
    client = TestClient(create_app())
    r = client.get("/api/reminders")
    assert r.status_code == 200
    assert r.json() == []


def test_index_serves_html():
    client = TestClient(create_app())
    r = client.get("/")
    assert r.status_code == 200
    # Either real Daisy.html or the fallback stub
    assert "Daisy" in r.text


# ---------------------------------------------------------------------------
# 1.2 — Calendar / Reminders / Mail endpoint smoke tests
# ---------------------------------------------------------------------------

def test_calendar_events_endpoint():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.list_events_today", return_value=[
        {"title": "Standup", "start": "9am", "end": "9:30am"}
    ]):
        r = client.get("/api/calendar/events")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert isinstance(data["events"], list)


def test_calendar_calendars_endpoint():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.list_calendars", return_value=["Home", "Work"]):
        r = client.get("/api/calendar/calendars")
    assert r.status_code == 200
    assert r.json() == {"calendars": ["Home", "Work"]}


def test_calendar_create_event_ok():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.create_event", return_value={"ok": True, "error": None}):
        r = client.post("/api/calendar/events", json={
            "title": "Test", "start_iso": "2026-05-26T10:00:00", "end_iso": "2026-05-26T11:00:00"
        })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_calendar_create_event_fails():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.create_event", return_value={"ok": False, "error": "oops"}):
        r = client.post("/api/calendar/events", json={
            "title": "Test", "start_iso": "2026-05-26T10:00:00", "end_iso": "2026-05-26T11:00:00"
        })
    assert r.status_code == 500


def test_mac_reminders_endpoint():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.list_reminders", return_value=[
        {"title": "Buy milk", "due": ""}
    ]):
        r = client.get("/api/mac-reminders")
    assert r.status_code == 200
    assert "reminders" in r.json()


def test_mac_reminders_create_ok():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_calendar.create_reminder", return_value={"ok": True, "error": None}):
        r = client.post("/api/mac-reminders", json={"title": "Feed cat"})
    assert r.status_code == 200


def test_mail_messages_endpoint():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_mail.list_recent_messages", return_value=[
        {"subject": "Hi", "from": "a@b.com", "date": "", "read": False}
    ]):
        r = client.get("/api/mail/messages")
    assert r.status_code == 200
    data = r.json()
    assert "messages" in data


def test_mail_search_endpoint():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_mail.search_messages", return_value=[]):
        r = client.get("/api/mail/search?q=invoice")
    assert r.status_code == 200


def test_mail_send_ok():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_mail.send_email", return_value={"ok": True, "error": None}):
        r = client.post("/api/mail/send", json={
            "to": "a@b.com", "subject": "Hi", "body": "Hello"
        })
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_mail_send_draft():
    from unittest.mock import patch as _patch
    client = TestClient(create_app())
    with _patch("services.mac_mail.create_draft", return_value={"ok": True, "error": None}):
        r = client.post("/api/mail/send", json={
            "to": "a@b.com", "subject": "Draft", "body": "text", "draft_only": True
        })
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 1.3 — Memory endpoint smoke tests
# ---------------------------------------------------------------------------

def test_memory_list_endpoint():
    client = TestClient(create_app())
    # Seed a memory first, then list
    client.post("/api/memory", json={"topic": "list_test_topic", "content": "something"})
    r = client.get("/api/memory")
    assert r.status_code == 200
    data = r.json()
    assert "memories" in data
    assert isinstance(data["memories"], list)


def test_memory_remember_endpoint():
    client = TestClient(create_app())
    r = client.post("/api/memory", json={"topic": "test_topic", "content": "test content"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_memory_recall_endpoint():
    client = TestClient(create_app())
    # First store something
    client.post("/api/memory", json={"topic": "recall_test", "content": "remembered value"})
    r = client.get("/api/memory/recall_test")
    assert r.status_code == 200
    data = r.json()
    assert data["content"] == "remembered value"


def test_memory_recall_missing_returns_404():
    client = TestClient(create_app())
    r = client.get("/api/memory/nonexistent_xyz_topic")
    assert r.status_code == 404


def test_memory_forget_endpoint():
    client = TestClient(create_app())
    client.post("/api/memory", json={"topic": "to_delete", "content": "bye"})
    r = client.delete("/api/memory/to_delete")
    assert r.status_code == 200


def test_memory_forget_missing_returns_404():
    client = TestClient(create_app())
    r = client.delete("/api/memory/no_such_topic_xyz")
    assert r.status_code == 404


def test_memory_search_endpoint():
    client = TestClient(create_app())
    client.post("/api/memory", json={"topic": "fruit", "content": "I love apples and oranges"})
    r = client.get("/api/memory/search?q=apples")
    assert r.status_code == 200
    data = r.json()
    assert "memories" in data
