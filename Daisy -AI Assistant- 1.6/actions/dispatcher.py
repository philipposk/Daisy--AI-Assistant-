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

    def dispatch_actions(
        self,
        actions: List[AssistantAction],
        auto_approve: bool = False,
        force_confirmation: bool = False,
        confirmation_provider=None,
    ) -> List[ActionResult]:
        """
        Dispatch a list of actions with safety checks.

        Args:
            actions: List of actions to execute
            auto_approve: Skip confirmation prompts. Only ever set by an
                explicit, trusted programmatic caller (e.g. the local HTTP
                client opting in per-request) — NEVER derived from LLM
                output. Auto-approved confirmations are audit-logged.
            force_confirmation: Adds a confirmation requirement on top of the
                safety checker's own per-action rules (e.g. when the LLM's
                intent flags the turn as sensitive). Can only ADD
                confirmation, never remove it.
            confirmation_provider: Optional per-call provider override so
                concurrent requests never mutate the shared instance.

        Returns:
            List of action results
        """
        results = []
        provider = confirmation_provider or self.confirmation_provider

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

            # 1.6: per-action confirmation requirement comes from the safety
            # checker OR the intent flag — auto_approve is the only thing
            # that can skip the prompt, and that skip is audit-logged.
            needs_confirmation = (
                self.safety_checker.requires_confirmation(action) or force_confirmation
            )
            if needs_confirmation and auto_approve:
                if self.audit_logger:
                    self.audit_logger.log_action(
                        action, approved=True, reason="Auto-approved by trusted client"
                    )
            if needs_confirmation and not auto_approve:
                if provider is None:
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
                    approved = provider.confirm(action, prompt)
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
