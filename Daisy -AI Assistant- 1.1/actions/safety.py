"""
Safety and permission checking layer
"""
import os
import shlex
from pathlib import Path
from typing import Optional, List
from schemas import AssistantAction
from config import Config
from utils import get_logger

logger = get_logger("safety")


# Fix #16: keyword sets used for token-level command-classification.
# Anything in here is matched against `basename(argv[0])` or whole tokens,
# never as a free-floating substring (so "su" no longer hits "sudo").
_NETWORK_BINS = {"curl", "wget", "nc", "netcat", "ssh", "scp", "rsync", "ftp", "sftp", "telnet"}
_SYSTEM_BINS = {"sudo", "su", "doas", "chmod", "chown", "mount", "umount", "diskutil", "launchctl"}


def _tokenize(command: str) -> List[str]:
    """Shell-tokenize a command, surviving quoting. Never raises."""
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _argv_bins(command: str) -> List[str]:
    """
    Return the set of program basenames the command would invoke, accounting
    for shell separators (|, &&, ;, ||). E.g.
        "curl x | tee y"     -> ["curl", "tee"]
        "VAR=1 env curl x"   -> ["curl"]
    """
    bins: List[str] = []
    tokens = _tokenize(command)
    next_is_bin = True
    for tok in tokens:
        if tok in ("|", "||", "&&", ";", "&"):
            next_is_bin = True
            continue
        if next_is_bin:
            # Skip env-style "VAR=value" prefixes
            if "=" in tok and tok.split("=", 1)[0].replace("_", "").isalnum() and not tok.startswith("/"):
                continue
            # Skip `env` itself; the next token is the real bin
            if os.path.basename(tok) == "env":
                continue
            bins.append(os.path.basename(tok))
            next_is_bin = False
    return bins


class SafetyChecker:
    """Checks actions for safety and permission compliance"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def check_action(self, action: AssistantAction) -> tuple[bool, Optional[str]]:
        """
        Check if an action is safe and allowed
        Returns: (is_allowed, reason_if_denied)
        """
        if action.action_type == "run_command" and action.run_command:
            return self._check_command(action.run_command.command)

        # 0.8: MCP tool calls allowed by default; safety on individual tools
        # is the server's responsibility; per-call confirmation handled separately.
        # Other action types are generally safe (notes, tasks, reminders).
        return True, None
    
    def _check_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Check if a command is safe to execute.

        Fixes #16 and #17: token-aware checks instead of free substring scans.
        - Blocked patterns: still substring (intentional — multi-word phrases
          like "rm -rf" need substring match), but lowered case-insensitively
          on the full command string.
        - Whitelist: compares basename(argv[0]) of EVERY piped/chained command
          against the whitelist. Absolute paths like /usr/bin/ls now work.
        - Network / system bins: matched as token basenames, so "su " no
          longer matches inside "sudo" and "curl" no longer matches
          inside "currently".
        """
        command_lower = command.lower()

        # 1. Blocked patterns (still substring — entries like `rm -rf`
        #    are intentionally multi-word phrases).
        for blocked in self.config.safety.blocked_commands:
            if blocked.lower() in command_lower:
                return False, f"Command contains blocked pattern: {blocked}"

        argv_bins = _argv_bins(command)

        # 2. Fix #16: network commands — "always block" beats "maybe whitelisted".
        if self.config.safety.block_network_commands:
            hit = next((b for b in argv_bins if b in _NETWORK_BINS), None)
            if hit:
                return False, f"Network commands are blocked ({hit})"

        # 3. Fix #16: system-modifying commands.
        if self.config.safety.block_system_modifying_commands:
            hit = next((b for b in argv_bins if b in _SYSTEM_BINS), None)
            if hit:
                return False, f"System-modifying commands are blocked ({hit})"

        # 4. Fix #17: whitelist (every chained command must be allowed).
        if self.config.safety.whitelisted_commands:
            wl = {os.path.basename(w) for w in self.config.safety.whitelisted_commands}
            if not argv_bins:
                return False, "Empty command"
            bad = [b for b in argv_bins if b not in wl]
            if bad:
                return False, f"Command not in whitelist: {bad[0]}"

        return True, None
    
    def requires_confirmation(self, action: AssistantAction) -> bool:
        """Check if action requires user confirmation."""
        if action.action_type == "run_command" and action.run_command:
            # Explicit flag wins
            if action.run_command.confirmation_required:
                return True

            # Fix #16: token-aware match — `rm` no longer fires for `from`,
            # `mv` no longer fires for `move-something`, etc.
            argv_bins = _argv_bins(action.run_command.command)
            patterns = {p.lower() for p in self.config.safety.require_confirmation_for}
            for b in argv_bins:
                if b.lower() in patterns:
                    return True

        # 0.8: an MCP tool call can opt into confirmation via its flag, and the
        # computer_use fallback is always confirmation-required (it drives the GUI).
        if action.action_type == "mcp_tool_call" and action.mcp_tool_call:
            if action.mcp_tool_call.confirmation_required:
                return True
            if action.mcp_tool_call.server == "computer_use":
                return True

        return False
    
    def check_working_directory(self, directory: Optional[str]) -> tuple[bool, Optional[str]]:
        """Check if working directory is allowed"""
        if not directory:
            return True, None
        
        dir_path = Path(directory).expanduser().resolve()
        
        # Check whitelisted directories
        if self.config.safety.whitelisted_directories:
            is_allowed = False
            for allowed_dir in self.config.safety.whitelisted_directories:
                allowed_path = Path(allowed_dir).expanduser().resolve()
                try:
                    # Check if directory is within an allowed directory
                    dir_path.relative_to(allowed_path)
                    is_allowed = True
                    break
                except ValueError:
                    continue
            
            if not is_allowed:
                return False, f"Directory not in whitelist: {directory}"
        
        # Check if directory exists
        if not dir_path.exists():
            return False, f"Directory does not exist: {directory}"
        
        # Check if it's actually a directory
        if not dir_path.is_dir():
            return False, f"Path is not a directory: {directory}"
        
        return True, None

