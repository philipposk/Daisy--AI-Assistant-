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


# --- 0.7 regression tests (fix #16-17: shlex-based safety) ---

def _checker_no_whitelist():
    """SafetyChecker with no whitelist (to test bin-based denial in isolation)."""
    cfg = create_test_config()
    cfg.safety.whitelisted_commands = []  # disable whitelist
    return SafetyChecker(cfg)


def test_curl_no_longer_matches_inside_word():
    """Substring scan used to match 'curl' inside 'currently' — must not."""
    checker = _checker_no_whitelist()
    action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="echo currently working"),
    )
    is_allowed, reason = checker.check_action(action)
    assert is_allowed == True, f"got blocked with reason={reason!r}"


def test_su_substring_no_longer_blocks_sudo_word_only():
    """A benign command containing the letters 'su' must pass; real 'sudo' still blocks."""
    # Local config: empty whitelist AND empty blocked-patterns (so we isolate the
    # token-based system-bins check from the substring blocked_commands check).
    cfg = create_test_config()
    cfg.safety.whitelisted_commands = []
    cfg.safety.blocked_commands = []
    checker = SafetyChecker(cfg)

    # 'sudo' is in _SYSTEM_BINS → blocked with a system reason.
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="sudo ls"))
    is_allowed, reason = checker.check_action(a)
    assert is_allowed == False, f"sudo should be blocked, got {reason!r}"
    assert "system" in reason.lower(), f"expected system reason, got {reason!r}"

    # A benign command containing the letters 'su' must pass (no substring collision).
    b = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="echo summary"))
    is_allowed, reason = checker.check_action(b)
    assert is_allowed == True, f"got blocked with reason={reason!r}"


def test_absolute_path_whitelist_allows_basename():
    """Whitelist should compare basenames so /usr/bin/ls is accepted."""
    cfg = create_test_config()
    cfg.safety.whitelisted_commands = ["ls"]
    checker = SafetyChecker(cfg)
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="/usr/bin/ls -la"))
    is_allowed, reason = checker.check_action(a)
    assert is_allowed == True, f"got blocked with reason={reason!r}"


def test_piped_command_each_piece_must_be_whitelisted():
    """Piped command: every basename must be allowed."""
    cfg = create_test_config()
    cfg.safety.whitelisted_commands = ["ls"]
    checker = SafetyChecker(cfg)
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="ls -la | grep py"))
    is_allowed, reason = checker.check_action(a)
    assert is_allowed == False
    assert "grep" in (reason or "")


def test_network_blocking_returns_network_reason():
    """Fix #22: network reason must beat whitelist-reason when both apply."""
    cfg = create_test_config()  # whitelist is ["ls", "pwd", "cd"] — curl not in it
    checker = SafetyChecker(cfg)
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="curl http://example.com"))
    is_allowed, reason = checker.check_action(a)
    assert is_allowed == False
    assert "network" in reason.lower(), f"expected network-reason, got {reason!r}"


def test_confirmation_token_aware():
    """'rm' confirmation pattern shouldn't fire on words like 'from' or 'remove-key'."""
    cfg = create_test_config()
    cfg.safety.whitelisted_commands = []
    checker = SafetyChecker(cfg)
    a = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="echo from now on"))
    assert checker.requires_confirmation(a) == False
    # but the real 'rm' must still confirm
    b = AssistantAction(action_type="run_command",
                        run_command=RunCommandAction(command="rm foo.txt"))
    assert checker.requires_confirmation(b) == True

