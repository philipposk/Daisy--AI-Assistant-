"""Tests for services/undo_stack.py (1.4)."""
import json
import tempfile
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.undo_stack import UndoStack, UndoEntry, UndoManager


# ---------------------------------------------------------------------------
# UndoStack
# ---------------------------------------------------------------------------

def test_push_and_pop():
    s = UndoStack()
    e = UndoEntry("create_note", "Create note: test")
    s.push(e)
    popped = s.pop()
    assert popped is e


def test_pop_empty_returns_none():
    s = UndoStack()
    assert s.pop() is None


def test_peek_does_not_remove():
    s = UndoStack()
    e = UndoEntry("create_task", "Create task: demo")
    s.push(e)
    assert s.peek() is e
    assert len(s) == 1


def test_list_returns_all():
    s = UndoStack()
    s.push(UndoEntry("create_note", "note1"))
    s.push(UndoEntry("create_task", "task1"))
    items = s.list()
    assert len(items) == 2
    assert items[0]["action_type"] == "create_note"
    assert items[1]["action_type"] == "create_task"


def test_max_size_enforced():
    s = UndoStack(max_size=3)
    for i in range(5):
        s.push(UndoEntry("create_note", f"note{i}"))
    assert len(s) == 3


# ---------------------------------------------------------------------------
# UndoManager
# ---------------------------------------------------------------------------

class _FakeCfg:
    class paths:
        tasks_file = ""
        reminders_file = ""
        notes_directory = ""


def _make_cfg(tmp_dir):
    cfg = type("cfg", (), {})()
    cfg.paths = type("paths", (), {})()
    cfg.paths.tasks_file = str(tmp_dir / "tasks.md")
    cfg.paths.reminders_file = str(tmp_dir / "reminders.json")
    cfg.paths.notes_directory = str(tmp_dir / "notes")
    return cfg


def test_undo_create_note_deletes_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        notes = tmp / "notes"
        notes.mkdir()
        note_file = notes / "test_note.md"
        note_file.write_text("# Test\n\ncontent")
        cfg = _make_cfg(tmp)
        manager = UndoManager(cfg)
        entry = UndoEntry("create_note", "Create note: test", metadata={"path": str(note_file)})
        result = manager.execute(entry)
    assert result["ok"] is True
    assert not note_file.exists()


def test_undo_create_note_already_gone():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_cfg(Path(tmpdir))
        manager = UndoManager(cfg)
        entry = UndoEntry("create_note", "note", metadata={"path": "/nonexistent/path/file.md"})
        result = manager.execute(entry)
    # File gone = ok=True (already done)
    assert result["ok"] is True


def test_undo_create_task_removes_line():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tasks = tmp / "tasks.md"
        tasks.write_text("- [ ] **Buy milk** - (Priority: medium)\n- [ ] **Walk dog** - (Priority: low)\n")
        cfg = _make_cfg(tmp)
        manager = UndoManager(cfg)
        entry = UndoEntry("create_task", "task", metadata={"title": "Buy milk"})
        result = manager.execute(entry)
        assert result["ok"] is True
        assert "Buy milk" not in tasks.read_text()


def test_undo_create_task_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        tasks = tmp / "tasks.md"
        tasks.write_text("- [ ] **Other task**\n")
        cfg = _make_cfg(tmp)
        manager = UndoManager(cfg)
        entry = UndoEntry("create_task", "t", metadata={"title": "Missing task"})
        result = manager.execute(entry)
    assert result["ok"] is False


def test_undo_create_reminder_removes_entry():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        reminders = tmp / "reminders.json"
        reminders.write_text(json.dumps([
            {"message": "drink water", "time": "2026-05-26T09:00:00"},
            {"message": "take meds", "time": "2026-05-26T20:00:00"},
        ]))
        cfg = _make_cfg(tmp)
        manager = UndoManager(cfg)
        entry = UndoEntry("create_reminder", "r", metadata={"message": "drink water"})
        result = manager.execute(entry)
        assert result["ok"] is True
        data = json.loads(reminders.read_text())
        assert len(data) == 1
        assert data[0]["message"] == "take meds"


def test_undo_memory_remember():
    from services.memory import MemoryStore
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_cfg(Path(tmpdir))
        store = MemoryStore(Path(tmpdir) / "mem.db")
        store.remember("fav_color", "blue")
        manager = UndoManager(cfg, memory_store=store)
        entry = UndoEntry("memory_remember", "m", metadata={"topic": "fav_color"})
        result = manager.execute(entry)
        assert result["ok"] is True
        assert store.recall("fav_color") is None


def test_undo_unsupported_type():
    cfg = _make_cfg(Path("/tmp"))
    manager = UndoManager(cfg)
    entry = UndoEntry("send_email", "email", metadata={})
    result = manager.execute(entry)
    assert result["ok"] is False
    assert "unsent" in result["error"].lower() or "cannot" in result["error"].lower()
