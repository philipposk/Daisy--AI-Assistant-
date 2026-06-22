"""
Tests for ConfirmationProvider (0.8).
"""
import io
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig, ConfirmationConfig
from services.confirmation import (
    AutoApproveConfirmation,
    AutoRejectConfirmation,
    CLIConfirmation,
    build_confirmation_provider,
    describe_action,
)
from schemas import AssistantAction, RunCommandAction, CreateNoteAction


def _cfg(mode: str = "cli") -> Config:
    return Config(
        stt=STTConfig(), llm=LLMConfig(), tts=TTSConfig(),
        safety=SafetyConfig(), paths=PathsConfig(),
        confirmation=ConfirmationConfig(mode=mode),
    )


def test_auto_approve_always_yes():
    p = AutoApproveConfirmation()
    a = AssistantAction(action_type="run_command", run_command=RunCommandAction(command="rm f"))
    assert p.confirm(a, "?") is True


def test_auto_reject_always_no():
    p = AutoRejectConfirmation()
    a = AssistantAction(action_type="run_command", run_command=RunCommandAction(command="rm f"))
    assert p.confirm(a, "?") is False


def test_cli_confirmation_reads_y():
    p = CLIConfirmation()
    a = AssistantAction(action_type="run_command", run_command=RunCommandAction(command="rm f"))
    # Simulate a TTY with 'y' typed
    with patch.object(sys.stdin, "isatty", return_value=True), \
         patch.object(sys.stdin, "readline", return_value="y\n"):
        assert p.confirm(a, "Run rm?") is True


def test_cli_confirmation_default_no():
    p = CLIConfirmation()
    a = AssistantAction(action_type="run_command", run_command=RunCommandAction(command="rm f"))
    with patch.object(sys.stdin, "isatty", return_value=True), \
         patch.object(sys.stdin, "readline", return_value="\n"):
        assert p.confirm(a, "?") is False


def test_cli_confirmation_no_tty_rejects():
    p = CLIConfirmation()
    a = AssistantAction(action_type="run_command", run_command=RunCommandAction(command="rm f"))
    with patch.object(sys.stdin, "isatty", return_value=False):
        assert p.confirm(a, "?") is False


def test_factory_picks_cli():
    prov = build_confirmation_provider(_cfg("cli"))
    assert isinstance(prov, CLIConfirmation)


def test_factory_picks_auto_approve():
    prov = build_confirmation_provider(_cfg("auto_approve"))
    assert isinstance(prov, AutoApproveConfirmation)


def test_factory_picks_auto_reject():
    prov = build_confirmation_provider(_cfg("auto_reject"))
    assert isinstance(prov, AutoRejectConfirmation)


def test_describe_action_command():
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="rm /tmp/x"))
    out = describe_action(a)
    assert "rm /tmp/x" in out


def test_describe_action_note():
    a = AssistantAction(action_type="create_note",
                        create_note=CreateNoteAction(title="Hi", content="..."))
    out = describe_action(a)
    assert "Hi" in out
