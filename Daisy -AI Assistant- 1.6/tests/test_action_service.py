"""
Tests for ActionService
"""
import tempfile
import json
from pathlib import Path
from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from services.action_service import ActionService
from schemas import AssistantAction, CreateNoteAction, CreateTaskAction, CreateReminderAction, RunCommandAction


def create_test_config(temp_dir: Path):
    """Create a test configuration with temp directories"""
    return Config(
        stt=STTConfig(),
        llm=LLMConfig(),
        tts=TTSConfig(),
        safety=SafetyConfig(
            whitelisted_commands=["ls", "pwd", "echo"],
            whitelisted_directories=[str(temp_dir)],
        ),
        paths=PathsConfig(
            notes_directory=str(temp_dir / "notes"),
            tasks_file=str(temp_dir / "tasks.md"),
            reminders_file=str(temp_dir / "reminders.json"),
            database_path=str(temp_dir / "test.db"),
        ),
    )


def test_create_note():
    """Test creating a note"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)
        
        note_action = CreateNoteAction(
            title="Test Note",
            content="This is test content"
        )
        action = AssistantAction(
            action_type="create_note",
            create_note=note_action
        )
        
        result = service.execute_action(action)
        assert result.success == True
        assert "Created note" in result.output
        
        # Check file was created
        notes_dir = tmp_path / "notes"
        note_files = list(notes_dir.glob("*.md"))
        assert len(note_files) > 0
        
        # Check content
        note_file = note_files[0]
        content = note_file.read_text()
        assert "Test Note" in content
        assert "This is test content" in content


def test_create_task():
    """Test creating a task"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)
        
        task_action = CreateTaskAction(
            title="Test Task",
            description="Do something",
            priority="high"
        )
        action = AssistantAction(
            action_type="create_task",
            create_task=task_action
        )
        
        result = service.execute_action(action)
        assert result.success == True
        
        # Check tasks file
        tasks_file = tmp_path / "tasks.md"
        assert tasks_file.exists()
        content = tasks_file.read_text()
        assert "Test Task" in content
        assert "high" in content


def test_create_reminder():
    """Test creating a reminder"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)
        
        reminder_action = CreateReminderAction(
            message="Call mom",
            reminder_time="2024-01-01T15:00:00"
        )
        action = AssistantAction(
            action_type="create_reminder",
            create_reminder=reminder_action
        )
        
        result = service.execute_action(action)
        assert result.success == True
        
        # Check reminders file
        reminders_file = tmp_path / "reminders.json"
        assert reminders_file.exists()
        
        with open(reminders_file, 'r') as f:
            reminders = json.load(f)
        
        assert len(reminders) > 0
        assert reminders[0]["message"] == "Call mom"


def test_run_command():
    """Test running a command"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)
        
        cmd_action = RunCommandAction(
            command="echo 'Hello World'",
            working_directory=str(tmp_path)
        )
        action = AssistantAction(
            action_type="run_command",
            run_command=cmd_action
        )
        
        result = service.execute_action(action)
        assert result.success == True
        assert "Hello World" in result.output


def test_run_command_blocked():
    """Test that blocked commands are rejected"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        config.safety.blocked_commands = ["rm -rf"]
        service = ActionService(config)
        
        cmd_action = RunCommandAction(command="rm -rf /tmp")
        action = AssistantAction(
            action_type="run_command",
            run_command=cmd_action
        )
        
        result = service.execute_action(action)
        assert result.success == False
        assert "blocked" in result.error.lower()


def test_conversation_action():
    """Test conversation action (no execution needed)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)

        action = AssistantAction(
            action_type="conversation",
            conversation="Hello, how can I help?"
        )

        result = service.execute_action(action)
        assert result.success == True
        assert result.output == "Hello, how can I help?"


# --- 0.7 regression tests ---


def test_note_collision_does_not_overwrite():
    """Fix #12: creating two notes with the same title must NOT silently overwrite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        service = ActionService(config)

        for content in ("first version", "second version"):
            note_action = CreateNoteAction(title="Dup Title", content=content)
            action = AssistantAction(action_type="create_note", create_note=note_action)
            result = service.execute_action(action)
            assert result.success

        notes_dir = tmp_path / "notes"
        files = sorted(notes_dir.glob("*.md"))
        assert len(files) == 2, f"expected 2 distinct files, got {[f.name for f in files]}"
        # First version untouched
        first = files[0].read_text()
        second = files[1].read_text()
        assert ("first version" in first and "second version" in second) or \
               ("first version" in second and "second version" in first)


def test_persistence_layer_is_shared():
    """Fix #13: ActionService writes via the shared PersistenceLayer schema."""
    from persistence import PersistenceLayer
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config = create_test_config(tmp_path)
        persistence = PersistenceLayer(Path(config.paths.database_path))
        service = ActionService(config, persistence=persistence)

        task_action = CreateTaskAction(title="Shared Task", priority="low")
        action = AssistantAction(action_type="create_task", create_task=task_action)
        result = service.execute_action(action)
        assert result.success

        rows = persistence.get_tasks()
        titles = [r["title"] for r in rows]
        assert "Shared Task" in titles



