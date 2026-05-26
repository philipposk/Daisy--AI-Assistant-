"""
Pydantic models for typed contracts in Daisy Assistant
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class TranscriptionSegment(BaseModel):
    """A segment of transcription with timestamp"""
    id: int
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str


class TranscriptionResult(BaseModel):
    """Result from Speech-to-Text transcription"""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    segments: Optional[List[TranscriptionSegment]] = None  # Timestamped segments


class ConversationMessage(BaseModel):
    """Message in conversation history"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


class CreateNoteAction(BaseModel):
    """Action to create a markdown note"""
    type: Literal["create_note"] = "create_note"
    title: str
    content: str
    path: Optional[str] = None  # If None, use configured notes directory
    tags: Optional[List[str]] = None


class CreateTaskAction(BaseModel):
    """Action to create a task"""
    type: Literal["create_task"] = "create_task"
    title: str
    description: Optional[str] = None
    priority: Optional[Literal["low", "medium", "high"]] = "medium"
    due_date: Optional[str] = None  # ISO format date string
    tags: Optional[List[str]] = None


class CreateReminderAction(BaseModel):
    """Action to create a reminder"""
    type: Literal["create_reminder"] = "create_reminder"
    message: str
    reminder_time: Optional[str] = None  # ISO format datetime string
    recurring: Optional[bool] = False


class RunCommandAction(BaseModel):
    """Action to run a command"""
    type: Literal["run_command"] = "run_command"
    command: str
    working_directory: Optional[str] = None
    timeout: Optional[int] = None  # seconds
    confirmation_required: bool = False


class MCPToolCallAction(BaseModel):
    """Action to call an MCP server's tool (0.8)."""
    type: Literal["mcp_tool_call"] = "mcp_tool_call"
    server: str                          # "desktop_automation" | "computer_use"
    tool: str                            # e.g. "take_screenshot", "build_with_retry"
    args: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 60
    confirmation_required: bool = False


class CreateCalendarEventAction(BaseModel):
    """Action to create a macOS Calendar event (1.2)."""
    type: Literal["create_calendar_event"] = "create_calendar_event"
    title: str
    start_iso: str                        # ISO 8601, e.g. "2026-05-26T15:00:00"
    end_iso: str
    calendar_name: Optional[str] = None
    notes: Optional[str] = None


class CreateMacReminderAction(BaseModel):
    """Action to create a macOS Reminders item (1.2)."""
    type: Literal["create_mac_reminder"] = "create_mac_reminder"
    title: str
    due_iso: Optional[str] = None
    list_name: Optional[str] = None
    notes: Optional[str] = None


class SendEmailAction(BaseModel):
    """Action to send an email via Mail.app (1.2)."""
    type: Literal["send_email"] = "send_email"
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    draft_only: bool = False              # True → create draft instead of sending


class AssistantAction(BaseModel):
    """Union of all action types - the LLM should output one of these"""
    action_type: Literal[
        "create_note", "create_task", "create_reminder",
        "run_command", "conversation", "mcp_tool_call",
        "create_calendar_event", "create_mac_reminder", "send_email",
    ]

    # Action payloads (only one should be populated based on action_type)
    create_note: Optional[CreateNoteAction] = None
    create_task: Optional[CreateTaskAction] = None
    create_reminder: Optional[CreateReminderAction] = None
    run_command: Optional[RunCommandAction] = None
    mcp_tool_call: Optional[MCPToolCallAction] = None
    create_calendar_event: Optional[CreateCalendarEventAction] = None
    create_mac_reminder: Optional[CreateMacReminderAction] = None
    send_email: Optional[SendEmailAction] = None
    conversation: Optional[str] = None  # Free-form response if no structured action
    
    # Metadata
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    
    class Config:
        # Pydantic v2 config
        use_enum_values = True
    
    # Note: Validation of required payloads is handled at construction time
    # rather than with validators to avoid Pydantic v2 complexity


class AssistantIntent(BaseModel):
    """Structured intent from user input"""
    transcript: str
    actions: List[AssistantAction]
    requires_confirmation: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


class ActionResult(BaseModel):
    """Result from executing an action"""
    action: AssistantAction
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    execution_time: Optional[float] = None  # seconds


