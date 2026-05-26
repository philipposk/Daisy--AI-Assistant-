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
    assert data["version"] == "0.9"
    assert isinstance(data["providers"], list)


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
