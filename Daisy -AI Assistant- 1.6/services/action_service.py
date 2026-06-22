"""
Action Service - Dispatcher that executes structured actions
Handles: CreateNote, CreateTask, CreateReminder, RunCommand
"""
import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from schemas import AssistantAction, ActionResult
from config import Config
from actions.safety import SafetyChecker
from persistence import PersistenceLayer
from utils import get_logger

logger = get_logger("action_service")


class ActionService:
    """Service that executes structured actions"""

    def __init__(self, config: Config, persistence: Optional[PersistenceLayer] = None,
                 mcp_registry=None):
        self.config = config
        self.safety_checker = SafetyChecker(config)
        # Fix #13: share a single PersistenceLayer instead of opening private
        # sqlite connections with a parallel `tasks` schema.
        if persistence is None:
            db_path = Path(config.paths.database_path).expanduser()
            persistence = PersistenceLayer(db_path)
        self.persistence = persistence

        # 0.8: optional MCP registry for mcp_tool_call actions.
        if mcp_registry is None:
            try:
                from services.mcp_client import MCPRegistry
                mcp_registry = MCPRegistry(config)
            except Exception:
                mcp_registry = None
        self.mcp_registry = mcp_registry

        self._ensure_paths()
    
    def _ensure_paths(self):
        """Ensure all configured paths exist"""
        notes_dir = Path(self.config.paths.notes_directory).expanduser()
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        tasks_file = Path(self.config.paths.tasks_file).expanduser()
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        
        reminders_file = Path(self.config.paths.reminders_file).expanduser()
        reminders_file.parent.mkdir(parents=True, exist_ok=True)
    
    def execute_action(self, action: AssistantAction) -> ActionResult:
        """
        Execute an action and return the result
        """
        import time
        start_time = time.time()
        
        try:
            if action.action_type == "create_note":
                result = self._execute_create_note(action)
            elif action.action_type == "create_task":
                result = self._execute_create_task(action)
            elif action.action_type == "create_reminder":
                result = self._execute_create_reminder(action)
            elif action.action_type == "run_command":
                result = self._execute_run_command(action)
            elif action.action_type == "mcp_tool_call":
                result = self._execute_mcp_tool_call(action)
            elif action.action_type == "create_calendar_event":
                result = self._execute_create_calendar_event(action)
            elif action.action_type == "create_mac_reminder":
                result = self._execute_create_mac_reminder(action)
            elif action.action_type == "send_email":
                result = self._execute_send_email(action)
            elif action.action_type == "conversation":
                # Conversation actions don't need execution
                result = ActionResult(
                    action=action,
                    success=True,
                    output=action.conversation or "",
                )
            else:
                result = ActionResult(
                    action=action,
                    success=False,
                    error=f"Unknown action type: {action.action_type}",
                )
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            result = ActionResult(
                action=action,
                success=False,
                error=str(e),
            )
        
        result.execution_time = time.time() - start_time
        return result
    
    def _execute_create_note(self, action: AssistantAction) -> ActionResult:
        """Create a markdown note"""
        if not action.create_note:
            raise ValueError("create_note payload missing")
        
        note_action = action.create_note
        notes_dir = Path(self.config.paths.notes_directory).expanduser().resolve()

        # Determine file path
        if note_action.path:
            # 1.6: confine LLM-supplied paths to the notes directory. A raw
            # path like "~/Library/LaunchAgents/x.md" or "../../etc" must not
            # escape; if it tries to, keep only the filename.
            requested = Path(note_action.path).expanduser()
            candidate = (notes_dir / requested).resolve() if not requested.is_absolute() else requested.resolve()
            try:
                candidate.relative_to(notes_dir)
                note_path = candidate
            except ValueError:
                logger.warning(
                    "Note path %s escapes notes directory; using basename only", requested
                )
                note_path = notes_dir / (requested.name or "untitled.md")
        else:
            # Create filename from title
            safe_title = "".join(c for c in note_action.title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_') or "untitled"
            note_path = notes_dir / f"{safe_title}.md"
            # Fix #12: don't overwrite an existing note with the same title.
            if note_path.exists():
                counter = 2
                while True:
                    candidate = notes_dir / f"{safe_title}_{counter}.md"
                    if not candidate.exists():
                        note_path = candidate
                        break
                    counter += 1

        note_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write note
        content = f"""# {note_action.title}

{note_action.content}

---
Created: {datetime.now().isoformat()}
"""
        if note_action.tags:
            content += f"Tags: {', '.join(note_action.tags)}\n"
        
        with open(note_path, 'w') as f:
            f.write(content)

        return ActionResult(
            action=action,
            success=True,
            output=f"Created note at {note_path}",
            metadata={"path": str(note_path)},
        )
    
    def _execute_create_task(self, action: AssistantAction) -> ActionResult:
        """Create a task"""
        if not action.create_task:
            raise ValueError("create_task payload missing")
        
        task_action = action.create_task
        
        # Append to tasks file
        tasks_file = Path(self.config.paths.tasks_file).expanduser()
        
        task_line = f"- [ ] **{task_action.title}**"
        if task_action.description:
            task_line += f" - {task_action.description}"
        if task_action.priority:
            task_line += f" (Priority: {task_action.priority})"
        if task_action.due_date:
            task_line += f" (Due: {task_action.due_date})"
        if task_action.tags:
            task_line += f" {', '.join(f'#{tag}' for tag in task_action.tags)}"
        task_line += "\n"
        
        with open(tasks_file, 'a') as f:
            f.write(task_line)
        
        # Fix #13: persist via the shared PersistenceLayer (no duplicate schema)
        try:
            self.persistence.save_task(
                title=task_action.title,
                description=task_action.description,
                priority=task_action.priority,
                due_date=task_action.due_date,
                tags=task_action.tags,
            )
        except Exception as e:
            logger.warning(f"Failed to save task to database: {e}")

        return ActionResult(
            action=action,
            success=True,
            output=f"Created task: {task_action.title}",
        )
    
    def _execute_create_reminder(self, action: AssistantAction) -> ActionResult:
        """Create a reminder"""
        if not action.create_reminder:
            raise ValueError("create_reminder payload missing")
        
        reminder_action = action.create_reminder

        # 1.6: read-modify-write under the shared reminders lock so the
        # scheduler thread can't clobber this write (and vice versa).
        from services.reminders_store import reminders_lock, read_reminders, write_reminders
        reminders_file = Path(self.config.paths.reminders_file).expanduser()
        created_at = datetime.now().isoformat()
        reminder = {
            "message": reminder_action.message,
            "reminder_time": reminder_action.reminder_time,
            "recurring": reminder_action.recurring,
            "created_at": created_at,
        }
        with reminders_lock():
            reminders = read_reminders(reminders_file)
            reminders.append(reminder)
            write_reminders(reminders_file, reminders)

        return ActionResult(
            action=action,
            success=True,
            output=f"Created reminder: {reminder_action.message}",
            metadata={"created_at": created_at},
        )
    
    def _execute_run_command(self, action: AssistantAction) -> ActionResult:
        """Execute a terminal command.

        Fix #14: the dispatcher already performed the safety check; we no
        longer repeat it here. BUT: when callers use ActionService directly
        (notably tests and one-off scripts) we still need a guard, so we
        keep a single defensive check rather than the previous duplicate.
        """
        if not action.run_command:
            raise ValueError("run_command payload missing")

        cmd_action = action.run_command

        # Defensive single safety check (idempotent w.r.t. dispatcher).
        is_allowed, reason = self.safety_checker.check_action(action)
        if not is_allowed:
            return ActionResult(
                action=action,
                success=False,
                error=f"Command blocked: {reason}",
            )

        # Check working directory
        working_dir = cmd_action.working_directory
        if working_dir:
            dir_allowed, dir_reason = self.safety_checker.check_working_directory(working_dir)
            if not dir_allowed:
                return ActionResult(
                    action=action,
                    success=False,
                    error=f"Directory not allowed: {dir_reason}",
                )
            working_dir = Path(working_dir).expanduser()
        
        # Execute command
        try:
            timeout = cmd_action.timeout or 60
            result = subprocess.run(
                cmd_action.command,
                shell=True,
                cwd=str(working_dir) if working_dir else None,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\nStderr: {result.stderr}"
            
            return ActionResult(
                action=action,
                success=result.returncode == 0,
                output=output,
                error=None if result.returncode == 0 else f"Command failed with exit code {result.returncode}",
            )
        except subprocess.TimeoutExpired:
            return ActionResult(
                action=action,
                success=False,
                error=f"Command timed out after {timeout} seconds",
            )
        except Exception as e:
            return ActionResult(
                action=action,
                success=False,
                error=f"Command execution error: {str(e)}",
            )

    def _execute_mcp_tool_call(self, action: AssistantAction) -> ActionResult:
        """0.8: dispatch an MCP tool call via the registry."""
        if not action.mcp_tool_call:
            raise ValueError("mcp_tool_call payload missing")
        if self.mcp_registry is None:
            return ActionResult(
                action=action, success=False,
                error="MCP registry unavailable in this build.",
            )

        call = action.mcp_tool_call
        client = self.mcp_registry.get(call.server)
        if client is None:
            return ActionResult(
                action=action, success=False,
                error=f"MCP server '{call.server}' is not configured/runnable.",
            )

        try:
            result = client.call_tool(call.tool, call.args or {}, timeout=call.timeout)
        except Exception as e:
            return ActionResult(
                action=action, success=False,
                error=f"MCP tool '{call.server}.{call.tool}' failed: {e}",
            )

        # MCP convention: result has `content` array of text/image blocks
        output_chunks = []
        for block in (result.get("content") or []):
            if isinstance(block, dict) and block.get("type") == "text":
                output_chunks.append(str(block.get("text", "")))
        output = "\n".join(output_chunks) if output_chunks else json.dumps(result)
        is_error = bool(result.get("isError"))

        return ActionResult(
            action=action,
            success=not is_error,
            output=output[:4000],  # truncate to keep audit log sane
            error=output[:1000] if is_error else None,
        )


    # ------------------------------------------------------------------
    # 1.2 — macOS native integrations
    # ------------------------------------------------------------------

    def _execute_create_calendar_event(self, action: AssistantAction) -> ActionResult:
        from services.mac_calendar import create_event
        if not action.create_calendar_event:
            return ActionResult(action=action, success=False, error="create_calendar_event payload missing")
        p = action.create_calendar_event
        res = create_event(
            title=p.title,
            start_iso=p.start_iso,
            end_iso=p.end_iso,
            calendar_name=p.calendar_name,
            notes=p.notes,
        )
        return ActionResult(
            action=action,
            success=res["ok"],
            output=f"Event '{p.title}' created" if res["ok"] else None,
            error=res.get("error"),
        )

    def _execute_create_mac_reminder(self, action: AssistantAction) -> ActionResult:
        from services.mac_calendar import create_reminder
        if not action.create_mac_reminder:
            return ActionResult(action=action, success=False, error="create_mac_reminder payload missing")
        p = action.create_mac_reminder
        res = create_reminder(
            title=p.title,
            due_iso=p.due_iso,
            list_name=p.list_name,
            notes=p.notes,
        )
        return ActionResult(
            action=action,
            success=res["ok"],
            output=f"Reminder '{p.title}' created" if res["ok"] else None,
            error=res.get("error"),
        )

    def _execute_send_email(self, action: AssistantAction) -> ActionResult:
        from services.mac_mail import send_email, create_draft
        if not action.send_email:
            return ActionResult(action=action, success=False, error="send_email payload missing")
        p = action.send_email
        if p.draft_only:
            res = create_draft(to=p.to, subject=p.subject, body=p.body)
            label = "Draft"
        else:
            res = send_email(to=p.to, subject=p.subject, body=p.body, cc=p.cc)
            label = "Email"
        return ActionResult(
            action=action,
            success=res["ok"],
            output=f"{label} sent to {p.to}" if res["ok"] else None,
            error=res.get("error"),
        )
