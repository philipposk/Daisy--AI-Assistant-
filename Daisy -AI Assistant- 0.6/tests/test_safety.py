"""
Tests for SafetyChecker
"""
from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from actions.safety import SafetyChecker
from schemas import AssistantAction, RunCommandAction


def create_test_config():
    """Create a test configuration"""
    return Config(
        stt=STTConfig(),
        llm=LLMConfig(),
        tts=TTSConfig(),
        safety=SafetyConfig(
            whitelisted_commands=["ls", "pwd", "cd"],
            whitelisted_directories=["/tmp", "~/test"],
            blocked_commands=["rm -rf", "sudo"],
            require_confirmation_for=["rm", "del"],
            block_network_commands=True,
            block_system_modifying_commands=True,
        ),
        paths=PathsConfig(),
    )


def test_safe_command():
    """Test that safe commands are allowed"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="ls -la")
    )
    
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == True
    assert reason is None


def test_blocked_command():
    """Test that blocked commands are denied"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="rm -rf /")
    )
    
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == False
    assert "blocked" in reason.lower()


def test_whitelist_enforcement():
    """Test that whitelist is enforced when configured"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    # Command not in whitelist
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="python script.py")
    )
    
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == False
    assert "whitelist" in reason.lower()


def test_network_command_blocking():
    """Test that network commands are blocked"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="curl http://example.com")
    )
    
    is_allowed, reason = checker.check_action(action)
    # Network commands should be blocked when block_network_commands is True
    if config.safety.block_network_commands:
        assert is_allowed == False
        assert reason is not None
        assert "network" in reason.lower() or "blocked" in reason.lower()
    else:
        # If blocking is disabled, command might be allowed
        pass


def test_system_command_blocking():
    """Test that system-modifying commands are blocked"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="sudo apt update")
    )
    
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == False
    assert "system" in reason.lower() or "blocked" in reason.lower()


def test_confirmation_required():
    """Test that dangerous commands require confirmation"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="rm file.txt")
    )
    
    requires = checker.requires_confirmation(action)
    assert requires == True


def test_safe_action_no_confirmation():
    """Test that safe actions don't require confirmation"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="ls")
    )
    
    requires = checker.requires_confirmation(action)
    assert requires == False


def test_working_directory_check():
    """Test working directory validation"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    # Allowed directory
    is_allowed, reason = checker.check_working_directory("/tmp")
    assert is_allowed == True
    
    # Not in whitelist
    is_allowed, reason = checker.check_working_directory("/root")
    assert is_allowed == False
    assert "whitelist" in reason.lower()


def test_non_command_actions_allowed():
    """Test that non-command actions are always allowed"""
    config = create_test_config()
    checker = SafetyChecker(config)
    
    from schemas import CreateNoteAction
    
    action = AssistantAction(
        action_type="create_note",
        create_note=CreateNoteAction(title="Test", content="Content")
    )
    
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == True

