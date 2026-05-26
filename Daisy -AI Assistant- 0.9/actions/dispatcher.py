"""
Action dispatcher - orchestrates action execution with safety checks
"""
from typing import List, Optional
from schemas import AssistantAction, ActionResult
from actions.safety import SafetyChecker
from config import Config
from utils import get_logger, AuditLogger

# Import ActionService here to avoid circular import
def _get_action_service(config, persistence=None):
    from services.action_service import ActionService
    return ActionService(config, persistence=persistence)

logger = get_logger("dispatcher")


class ActionDispatcher:
    """Orchestrates action execution with safety checks and audit logging."""

    def __init__(
        self,
        config: Config,
        audit_logger: Optional[AuditLogger] = None,
        confirmation_provider=None,   # 0.8: pluggable ConfirmationProvider
        persistence=None,             # 0.8: shared PersistenceLayer (0.7 fix #13)
    ):
        self.config = config
        self.safety_checker = SafetyChecker(config)
        # Lazy import to avoid circular dependency
        self._action_service = None
        self._persistence = persistence
        self.audit_logger = audit_logger
        self.confirmation_provider = confirmation_provider

    @property
    def action_service(self):
        """Lazy load ActionService to avoid circular import"""
        if self._action_service is None:
            self._action_service = _get_action_service(self.config, persistence=self._persistence)
        return self._action_service

    def dispatch_actions(self, actions: List[AssistantAction], auto_approve: bool = False) -> List[ActionResult]:
        """
        Dispatch a list of actions with safety checks.

        Args:
            actions: List of actions to execute
            auto_approve: If True, skip confirmation prompts altogether. The
                confirmation_provider is the preferred path; auto_approve is
                kept for backward compatibility and for trusted programmatic
                callers.

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

            # 0.8: real confirmation prompt if a provider is wired in.
            if self.safety_checker.requires_confirmation(action) and not auto_approve:
                if self.confirmation_provider is None:
                    # Fall back to the 0.7 behaviour: surface a failed result.
                    logger.warning(
                        f"Action requires confirmation but no ConfirmationProvider; rejecting: {action.action_type}"
                    )
                    if self.audit_logger:
                        self.audit_logger.log_action(action, approved=False, reason="Confirmation required (no provider)")
                    results.append(ActionResult(
                        action=action,
                        success=False,
                        error="Confirmation required (no provider wired).",
                    ))
                    continue

                from services.confirmation import describe_action
                prompt = describe_action(action)
                try:
                    approved = self.confirmation_provider.confirm(action, prompt)
                except Exception as e:
                    logger.warning(f"ConfirmationProvider raised: {e}; treating as reject.")
                    approved = False

                if not approved:
                    if self.audit_logger:
                        self.audit_logger.log_action(action, approved=False, reason="Declined by user")
                    results.append(ActionResult(
                        action=action,
                        success=False,
                        error="Declined by user.",
                    ))
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
