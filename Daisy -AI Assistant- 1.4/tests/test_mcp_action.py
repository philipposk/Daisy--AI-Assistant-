"""
Tests for the mcp_tool_call action path (0.8).
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from schemas import AssistantAction, MCPToolCallAction
from services.action_service import ActionService
from actions.dispatcher import ActionDispatcher
from services.confirmation import AutoApproveConfirmation


def _cfg(tmp: Path) -> Config:
    return Config(
        stt=STTConfig(), llm=LLMConfig(), tts=TTSConfig(),
        safety=SafetyConfig(), paths=PathsConfig(
            notes_directory=str(tmp / "notes"),
            tasks_file=str(tmp / "tasks.md"),
            reminders_file=str(tmp / "reminders.json"),
            database_path=str(tmp / "test.db"),
        ),
    )


def test_mcp_tool_call_schema():
    """Schema accepts the new mcp_tool_call action_type."""
    a = AssistantAction(
        action_type="mcp_tool_call",
        mcp_tool_call=MCPToolCallAction(
            server="desktop_automation",
            tool="take_screenshot",
            args={"region": "full"},
        ),
    )
    assert a.action_type == "mcp_tool_call"
    assert a.mcp_tool_call.tool == "take_screenshot"


def test_action_service_dispatches_to_mcp_registry():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = _cfg(tmp)
        fake_registry = MagicMock()
        fake_client = MagicMock()
        fake_client.call_tool.return_value = {
            "content": [{"type": "text", "text": "saved screenshot to /tmp/x.png"}],
        }
        fake_registry.get.return_value = fake_client
        svc = ActionService(cfg, mcp_registry=fake_registry)
        action = AssistantAction(
            action_type="mcp_tool_call",
            mcp_tool_call=MCPToolCallAction(
                server="desktop_automation",
                tool="take_screenshot",
                args={"region": "full"},
            ),
        )
        result = svc.execute_action(action)
        assert result.success is True
        assert "saved screenshot" in result.output
        fake_registry.get.assert_called_once_with("desktop_automation")
        fake_client.call_tool.assert_called_once_with("take_screenshot", {"region": "full"}, timeout=60)


def test_action_service_mcp_server_unavailable():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = _cfg(tmp)
        fake_registry = MagicMock()
        fake_registry.get.return_value = None
        svc = ActionService(cfg, mcp_registry=fake_registry)
        action = AssistantAction(
            action_type="mcp_tool_call",
            mcp_tool_call=MCPToolCallAction(server="desktop_automation", tool="x"),
        )
        result = svc.execute_action(action)
        assert result.success is False
        assert "desktop_automation" in result.error


def test_computer_use_requires_confirmation_and_dispatcher_blocks_without_provider():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = _cfg(tmp)
        dispatcher = ActionDispatcher(cfg)
        action = AssistantAction(
            action_type="mcp_tool_call",
            mcp_tool_call=MCPToolCallAction(server="computer_use", tool="goal",
                                            args={"goal": "open Maps"}),
        )
        results = dispatcher.dispatch_actions([action], auto_approve=False)
        assert results[0].success is False
        # No provider → fallback path returns "Confirmation required" message
        assert "confirmation" in (results[0].error or "").lower()


def test_computer_use_runs_when_user_approves():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cfg = _cfg(tmp)
        fake_registry = MagicMock()
        fake_client = MagicMock()
        fake_client.call_tool.return_value = {"content": [{"type": "text", "text": "ok"}]}
        fake_registry.get.return_value = fake_client
        dispatcher = ActionDispatcher(
            cfg,
            confirmation_provider=AutoApproveConfirmation(),
        )
        # Inject a stub action service that uses our fake registry
        from services.action_service import ActionService as _AS
        dispatcher._action_service = _AS(cfg, mcp_registry=fake_registry)

        action = AssistantAction(
            action_type="mcp_tool_call",
            mcp_tool_call=MCPToolCallAction(server="computer_use", tool="goal",
                                            args={"goal": "open Maps"}),
        )
        results = dispatcher.dispatch_actions([action], auto_approve=False)
        assert results[0].success is True
        assert "ok" in results[0].output
