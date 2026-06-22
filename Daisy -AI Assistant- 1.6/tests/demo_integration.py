#!/usr/bin/env python3
"""
Integration test/demo showing Daisy pipeline working
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from schemas import TranscriptionResult, AssistantAction, CreateNoteAction, CreateTaskAction
from services.brain_service import BrainService
from actions.safety import SafetyChecker
from services.action_service import ActionService
from actions.dispatcher import ActionDispatcher
from utils.audit import AuditLogger


def demo_schema_validation():
    """Demo: Schema validation"""
    print("\n" + "="*60)
    print("📋 Demo 1: Schema Validation")
    print("="*60)
    
    from schemas import TranscriptionResult, AssistantAction, CreateNoteAction
    
    # Create a transcription result
    transcript = TranscriptionResult(text="Create a note about Python")
    print(f"✅ Created TranscriptionResult: '{transcript.text}'")
    
    # Create an action
    note_action = CreateNoteAction(
        title="Python Notes",
        content="Python is a programming language"
    )
    action = AssistantAction(
        action_type="create_note",
        create_note=note_action
    )
    print(f"✅ Created AssistantAction: {action.action_type}")
    print(f"   Title: {action.create_note.title}")
    print(f"   Content: {action.create_note.content[:30]}...")


def demo_safety_checker():
    """Demo: Safety checking"""
    print("\n" + "="*60)
    print("🛡️  Demo 2: Safety Checker")
    print("="*60)
    
    config = Config(
        stt=STTConfig(),
        llm=LLMConfig(),
        tts=TTSConfig(),
        safety=SafetyConfig(
            blocked_commands=["rm -rf", "sudo"],
            whitelisted_commands=["ls", "pwd", "echo"],
            block_network_commands=True,
        ),
        paths=PathsConfig(),
    )
    
    checker = SafetyChecker(config)
    
    # Test safe command
    from schemas import RunCommandAction
    safe_action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="ls")
    )
    
    is_allowed, reason = checker.check_action(safe_action)
    print(f"✅ Safe command 'ls': Allowed={is_allowed}")
    
    # Test blocked command
    blocked_action = AssistantAction(
        action_type="run_command",
        run_command=RunCommandAction(command="rm -rf /")
    )
    is_allowed, reason = checker.check_action(blocked_action)
    print(f"❌ Blocked command 'rm -rf /': Allowed={is_allowed}, Reason={reason}")


def demo_action_execution():
    """Demo: Action execution"""
    print("\n" + "="*60)
    print("⚙️  Demo 3: Action Execution")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        config = Config(
            stt=STTConfig(),
            llm=LLMConfig(),
            tts=TTSConfig(),
            safety=SafetyConfig(
                whitelisted_commands=["echo"],
                whitelisted_directories=[str(tmp_path)],
            ),
            paths=PathsConfig(
                notes_directory=str(tmp_path / "notes"),
                tasks_file=str(tmp_path / "tasks.md"),
                reminders_file=str(tmp_path / "reminders.json"),
                database_path=str(tmp_path / "test.db"),
            ),
        )
        
        service = ActionService(config)
        
        # Create a note
        note_action = CreateNoteAction(
            title="Demo Note",
            content="This is a demo note created by the test"
        )
        action = AssistantAction(
            action_type="create_note",
            create_note=note_action
        )
        
        result = service.execute_action(action)
        print(f"✅ Create Note Action:")
        print(f"   Success: {result.success}")
        print(f"   Output: {result.output}")
        
        # Check file was created
        notes_dir = tmp_path / "notes"
        if notes_dir.exists():
            note_files = list(notes_dir.glob("*.md"))
            if note_files:
                print(f"   File created: {note_files[0].name}")
                content = note_files[0].read_text()
                print(f"   Content preview: {content[:50]}...")


def demo_brain_parsing():
    """Demo: Brain service JSON parsing"""
    print("\n" + "="*60)
    print("🧠 Demo 4: Brain Service - Action Parsing")
    print("="*60)
    
    config = Config(
        stt=STTConfig(),
        llm=LLMConfig(),
        tts=TTSConfig(),
        safety=SafetyConfig(),
        paths=PathsConfig(),
    )
    
    service = BrainService(config)
    
    # Simulate LLM JSON response
    llm_response = {
        "actions": [
            {
                "action_type": "create_note",
                "create_note": {
                    "title": "Meeting Notes",
                    "content": "Discussed project timeline"
                },
                "confidence": 0.95,
                "reasoning": "User wants to save meeting information"
            },
            {
                "action_type": "create_task",
                "create_task": {
                    "title": "Follow up on action items",
                    "priority": "high"
                }
            }
        ],
        "requires_confirmation": False
    }
    
    actions = service._parse_actions(llm_response)
    print(f"✅ Parsed {len(actions)} actions from LLM response:")
    for i, action in enumerate(actions, 1):
        print(f"   {i}. {action.action_type}")
        if action.action_type == "create_note":
            print(f"      Title: {action.create_note.title}")
        elif action.action_type == "create_task":
            print(f"      Title: {action.create_task.title}")


def demo_persistence():
    """Demo: Persistence layer"""
    print("\n" + "="*60)
    print("💾 Demo 5: Persistence Layer")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "demo.db"
        from persistence.database import PersistenceLayer
        from schemas import ConversationMessage
        
        persistence = PersistenceLayer(db_path)
        
        # Save a task
        task_id = persistence.save_task(
            title="Demo Task",
            description="This is a demo task",
            priority="medium"
        )
        print(f"✅ Saved task with ID: {task_id}")
        
        # Get tasks
        tasks = persistence.get_tasks()
        print(f"✅ Retrieved {len(tasks)} task(s)")
        if tasks:
            print(f"   Task: {tasks[0]['title']}")
        
        # Save conversation message
        msg = ConversationMessage(
            role="user",
            content="Hello, Daisy!"
        )
        msg_id = persistence.save_conversation_message(msg)
        print(f"✅ Saved conversation message with ID: {msg_id}")
        
        # Get recent messages
        messages = persistence.get_recent_messages(limit=5)
        print(f"✅ Retrieved {len(messages)} conversation message(s)")


def main():
    """Run all demos"""
    print("🌟 Daisy Assistant 0.6 - Integration Demo")
    print("="*60)
    print("This demo shows the core functionality working:")
    print("  • Schema validation")
    print("  • Safety checking")
    print("  • Action execution")
    print("  • Brain service parsing")
    print("  • Persistence layer")
    
    try:
        demo_schema_validation()
        demo_safety_checker()
        demo_action_execution()
        demo_brain_parsing()
        demo_persistence()
        
        print("\n" + "="*60)
        print("✅ All demos completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

