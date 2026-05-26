"""
Tests for Pydantic schemas
"""
from datetime import datetime
from schemas.models import (
    TranscriptionResult,
    ConversationMessage,
    CreateNoteAction,
    CreateTaskAction,
    CreateReminderAction,
    RunCommandAction,
    AssistantAction,
    AssistantIntent,
    ActionResult,
)


def test_transcription_result():
    """Test TranscriptionResult schema"""
    result = TranscriptionResult(text="Hello world")
    assert result.text == "Hello world"
    assert result.timestamp is not None
    
    result2 = TranscriptionResult(
        text="Test",
        language="en",
        confidence=0.95,
        duration=2.5
    )
    assert result2.language == "en"
    assert result2.confidence == 0.95


def test_conversation_message():
    """Test ConversationMessage schema"""
    msg = ConversationMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.timestamp is not None


def test_create_note_action():
    """Test CreateNoteAction schema"""
    action = CreateNoteAction(
        title="Test Note",
        content="This is a test"
    )
    assert action.title == "Test Note"
    assert action.content == "This is a test"
    assert action.type == "create_note"
    
    action_with_tags = CreateNoteAction(
        title="Note",
        content="Content",
        tags=["python", "testing"]
    )
    assert len(action_with_tags.tags) == 2


def test_create_task_action():
    """Test CreateTaskAction schema"""
    action = CreateTaskAction(
        title="Test Task",
        description="Do something",
        priority="high"
    )
    assert action.title == "Test Task"
    assert action.priority == "high"
    assert action.type == "create_task"


def test_create_reminder_action():
    """Test CreateReminderAction schema"""
    action = CreateReminderAction(
        message="Call mom",
        reminder_time="2024-01-01T15:00:00"
    )
    assert action.message == "Call mom"
    assert action.recurring == False


def test_run_command_action():
    """Test RunCommandAction schema"""
    action = RunCommandAction(
        command="ls -la",
        working_directory="/tmp",
        confirmation_required=True
    )
    assert action.command == "ls -la"
    assert action.confirmation_required == True


def test_assistant_action_create_note():
    """Test AssistantAction with create_note"""
    note_action = CreateNoteAction(title="Note", content="Content")
    action = AssistantAction(
        action_type="create_note",
        create_note=note_action
    )
    assert action.action_type == "create_note"
    assert action.create_note is not None


def test_assistant_action_conversation():
    """Test AssistantAction with conversation"""
    action = AssistantAction(
        action_type="conversation",
        conversation="Hello, how can I help?"
    )
    assert action.action_type == "conversation"
    assert action.conversation == "Hello, how can I help?"


def test_assistant_intent():
    """Test AssistantIntent schema"""
    action = AssistantAction(
        action_type="conversation",
        conversation="Response"
    )
    intent = AssistantIntent(
        transcript="User said hello",
        actions=[action]
    )
    assert intent.transcript == "User said hello"
    assert len(intent.actions) == 1
    assert intent.requires_confirmation == False


def test_action_result():
    """Test ActionResult schema"""
    action = AssistantAction(
        action_type="conversation",
        conversation="Test"
    )
    result = ActionResult(
        action=action,
        success=True,
        output="Success message"
    )
    assert result.success == True
    assert result.output == "Success message"
    assert result.error is None

