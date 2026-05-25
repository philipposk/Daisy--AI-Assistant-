"""
Safety and permission checking layer
"""
import os
from pathlib import Path
from typing import Optional
from schemas import AssistantAction
from config import Config
from utils import get_logger

logger = get_logger("safety")


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
        
        # Other action types are generally safe (notes, tasks, reminders)
        return True, None
    
    def _check_command(self, command: str) -> tuple[bool, Optional[str]]:
        """Check if a command is safe to execute"""
        command_lower = command.lower()
        
        # Check blocked commands
        for blocked in self.config.safety.blocked_commands:
            if blocked.lower() in command_lower:
                return False, f"Command contains blocked pattern: {blocked}"
        
        # Check whitelist (if whitelist exists and command not in it, deny)
        if self.config.safety.whitelisted_commands:
            # Check if command starts with any whitelisted command
            is_whitelisted = any(
                command.startswith(wl_cmd) for wl_cmd in self.config.safety.whitelisted_commands
            )
            if not is_whitelisted:
                return False, "Command not in whitelist"
        
        # Check for network commands
        if self.config.safety.block_network_commands:
            network_keywords = ["curl", "wget", "nc ", "netcat", "ssh ", "scp ", "rsync"]
            if any(keyword in command_lower for keyword in network_keywords):
                return False, "Network commands are blocked"
        
        # Check for system-modifying commands
        if self.config.safety.block_system_modifying_commands:
            system_keywords = ["sudo", "su ", "chmod", "chown", "mount", "umount"]
            if any(keyword in command_lower for keyword in system_keywords):
                return False, "System-modifying commands are blocked"
        
        return True, None
    
    def requires_confirmation(self, action: AssistantAction) -> bool:
        """Check if action requires user confirmation"""
        if action.action_type == "run_command" and action.run_command:
            # Check if explicitly marked
            if action.run_command.confirmation_required:
                return True
            
            # Check against confirmation patterns
            command = action.run_command.command.lower()
            for pattern in self.config.safety.require_confirmation_for:
                if pattern.lower() in command:
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

