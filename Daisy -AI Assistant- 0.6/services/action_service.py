"""
Action Service - Dispatcher that executes structured actions
Handles: CreateNote, CreateTask, CreateReminder, RunCommand
"""
import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import sqlite3

from schemas import AssistantAction, ActionResult
from config import Config
from actions.safety import SafetyChecker
from utils import get_logger

logger = get_logger("action_service")


class ActionService:
    """Service that executes structured actions"""
    
    def __init__(self, config: Config):
        self.config = config
        self.safety_checker = SafetyChecker(config)
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
        
        # Determine file path
        if note_action.path:
            note_path = Path(note_action.path).expanduser()
        else:
            notes_dir = Path(self.config.paths.notes_directory).expanduser()
            # Create filename from title
            safe_title = "".join(c for c in note_action.title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title.replace(' ', '_')
            note_path = notes_dir / f"{safe_title}.md"
        
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
        
        # Also save to database if available
        try:
            self._save_task_to_db(task_action)
        except Exception as e:
            logger.warning(f"Failed to save task to database: {e}")
        
        return ActionResult(
            action=action,
            success=True,
            output=f"Created task: {task_action.title}",
        )
    
    def _save_task_to_db(self, task_action):
        """Save task to SQLite database"""
        db_path = Path(self.config.paths.database_path).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT,
                due_date TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT 0
            )
        """)
        
        # Insert task
        cursor.execute("""
            INSERT INTO tasks (title, description, priority, due_date, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_action.title,
            task_action.description,
            task_action.priority,
            task_action.due_date,
            json.dumps(task_action.tags) if task_action.tags else None,
        ))
        
        conn.commit()
        conn.close()
    
    def _execute_create_reminder(self, action: AssistantAction) -> ActionResult:
        """Create a reminder"""
        if not action.create_reminder:
            raise ValueError("create_reminder payload missing")
        
        reminder_action = action.create_reminder
        
        # Load existing reminders
        reminders_file = Path(self.config.paths.reminders_file).expanduser()
        reminders = []
        if reminders_file.exists():
            with open(reminders_file, 'r') as f:
                try:
                    reminders = json.load(f)
                except json.JSONDecodeError:
                    reminders = []
        
        # Add new reminder
        reminder = {
            "message": reminder_action.message,
            "reminder_time": reminder_action.reminder_time,
            "recurring": reminder_action.recurring,
            "created_at": datetime.now().isoformat(),
        }
        reminders.append(reminder)
        
        # Save reminders
        with open(reminders_file, 'w') as f:
            json.dump(reminders, f, indent=2)
        
        return ActionResult(
            action=action,
            success=True,
            output=f"Created reminder: {reminder_action.message}",
        )
    
    def _execute_run_command(self, action: AssistantAction) -> ActionResult:
        """Execute a terminal command"""
        if not action.run_command:
            raise ValueError("run_command payload missing")
        
        cmd_action = action.run_command
        
        # Safety check
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

