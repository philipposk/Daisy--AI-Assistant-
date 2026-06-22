"""
Tests for PersistenceLayer
"""
import tempfile
from pathlib import Path
from persistence.database import PersistenceLayer
from schemas import ConversationMessage


def test_save_and_get_task():
    """Test saving and retrieving tasks"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = PersistenceLayer(db_path)
        
        # Save task
        task_id = persistence.save_task(
            title="Test Task",
            description="Do something",
            priority="high",
            tags=["python", "testing"]
        )
        
        assert task_id > 0
        
        # Get tasks
        tasks = persistence.get_tasks(completed=False)
        assert len(tasks) > 0
        assert tasks[0]["title"] == "Test Task"
        assert tasks[0]["priority"] == "high"
        assert len(tasks[0]["tags"]) == 2


def test_complete_task():
    """Test marking task as completed"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = PersistenceLayer(db_path)
        
        # Save task
        task_id = persistence.save_task(title="Complete Me")
        
        # Complete it
        success = persistence.complete_task(task_id)
        assert success == True
        
        # Check it's marked as completed
        completed_tasks = persistence.get_tasks(completed=True)
        assert len(completed_tasks) > 0
        assert completed_tasks[0]["completed"] == 1


def test_save_conversation_message():
    """Test saving conversation messages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = PersistenceLayer(db_path)
        
        message = ConversationMessage(
            role="user",
            content="Hello, Daisy!"
        )
        
        msg_id = persistence.save_conversation_message(message)
        assert msg_id > 0


def test_get_recent_messages():
    """Test retrieving recent conversation messages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = PersistenceLayer(db_path)
        
        # Save multiple messages
        for i in range(5):
            message = ConversationMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            persistence.save_conversation_message(message)
        
        # Get recent messages
        messages = persistence.get_recent_messages(limit=3)
        assert len(messages) == 3
        assert messages[-1].content == "Message 4"  # Most recent


def test_clear_old_messages():
    """Test clearing old messages"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        persistence = PersistenceLayer(db_path)
        
        # Save many messages
        for i in range(20):
            message = ConversationMessage(
                role="user",
                content=f"Message {i}"
            )
            persistence.save_conversation_message(message)
        
        # Clear old, keep last 10
        persistence.clear_old_messages(keep_last_n=10)
        
        # Check only 10 remain
        messages = persistence.get_recent_messages(limit=20)
        assert len(messages) == 10



