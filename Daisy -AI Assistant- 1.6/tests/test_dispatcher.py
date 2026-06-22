"""
Tests for ActionDispatcher (0.7 fix #15).
"""
import tempfile
from pathlib import Path
from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from actions.dispatcher import ActionDispatcher
from schemas import AssistantAction, RunCommandAction


def _config(tmp_path: Path) -> Config:
    return Config(
        stt=STTConfig(), llm=LLMConfig(), tts=TTSConfig(),
        safety=SafetyConfig(
            whitelisted_commands=[],            # no whitelist (so rm reaches the confirm path)
            require_confirmation_for=["rm"],    # rm requires confirmation
            block_network_commands=False,
            block_system_modifying_commands=False,
        ),
        paths=PathsConfig(
            notes_directory=str(tmp_path / "notes"),
            tasks_file=str(tmp_path / "tasks.md"),
            reminders_file=str(tmp_path / "reminders.json"),
            database_path=str(tmp_path / "test.db"),
        ),
    )


def test_confirmation_required_returns_failed_result():
    """
    Fix #15: dispatcher must NOT silently skip a confirmation-required action;
    it must return a failed ActionResult so callers can surface the message.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cfg = _config(tmp_path)
        dispatcher = ActionDispatcher(cfg)

        action = AssistantAction(
            action_type="run_command",
            run_command=RunCommandAction(command="rm foo.txt"),
        )
        results = dispatcher.dispatch_actions([action], auto_approve=False)
        assert len(results) == 1
        r = results[0]
        assert r.success is False
        assert r.error and "confirmation" in r.error.lower()


def test_auto_approve_executes_confirmation_action():
    """When auto_approve=True, the same action should execute."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cfg = _config(tmp_path)
        # Make it a benign command that still trips 'rm' confirmation pattern? No,
        # 'rm' really needs to be the bin. Create a file the action will delete.
        target = tmp_path / "to_delete.txt"
        target.write_text("bye")
        dispatcher = ActionDispatcher(cfg)
        action = AssistantAction(
            action_type="run_command",
            run_command=RunCommandAction(command=f"rm {target}"),
        )
        results = dispatcher.dispatch_actions([action], auto_approve=True)
        assert len(results) == 1
        assert results[0].success is True
        assert not target.exists()
