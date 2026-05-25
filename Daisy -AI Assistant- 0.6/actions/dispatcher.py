"""
Action dispatcher - orchestrates action execution with safety checks
"""
from typing import List, Optional
from schemas import AssistantAction, ActionResult
from actions.safety import SafetyChecker
from config import Config
from utils import get_logger, AuditLogger

# Import ActionService here to avoid circular import
def _get_action_service(config):
    from services.action_service import ActionService
    return ActionService(config)

logger = get_logger("dispatcher")


class ActionDispatcher:
    """Orchestrates action execution with safety checks and audit logging"""
    
    def __init__(self, config: Config, audit_logger: Optional[AuditLogger] = None):
        self.config = config
        self.safety_checker = SafetyChecker(config)
        # Lazy import to avoid circular dependency
        self._action_service = None
        self.audit_logger = audit_logger
    
    @property
    def action_service(self):
        """Lazy load ActionService to avoid circular import"""
        if self._action_service is None:
            self._action_service = _get_action_service(self.config)
        return self._action_service
    
    def dispatch_actions(self, actions: List[AssistantAction], auto_approve: bool = False) -> List[ActionResult]:
        """
        Dispatch a list of actions with safety checks
        
        Args:
            actions: List of actions to execute
            auto_approve: If True, skip confirmation for actions that require it
        
        Returns:
            List of action results
        """
        results = []
        
        for action in actions:
            # Skip conversation actions (they're already handled)
            if action.action_type == "conversation":
                continue
            
            # Safety check
            is_allowed, reason = self.safety_checker.check_action(action)
            if not is_allowed:
                result = ActionResult(
                    action=action,
                    success=False,
                    error=f"Action blocked: {reason}",
                )
                results.append(result)
                
                if self.audit_logger:
                    self.audit_logger.log_action(action, approved=False, reason=reason)
                continue
            
            # Check if confirmation required
            if self.safety_checker.requires_confirmation(action) and not auto_approve:
                # In a real implementation, this would prompt the user
                # For now, we'll log and skip if not auto-approved
                logger.warning(f"Action requires confirmation: {action.action_type}")
                if self.audit_logger:
                    self.audit_logger.log_action(action, approved=False, reason="Confirmation required")
                continue
            
            # Log approval
            if self.audit_logger:
                self.audit_logger.log_action(action, approved=True)
            
            # Execute action
            result = self.action_service.execute_action(action)
            results.append(result)
            
            # Log execution
            if self.audit_logger:
                self.audit_logger.log_execution(result)
        
        return results

