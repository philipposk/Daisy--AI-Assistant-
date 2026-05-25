"""
Tests for BrainService action parsing
"""
from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from services.brain_service import BrainService
from schemas import TranscriptionResult


def create_test_config():
    """Create a test configuration"""
    return Config(
        stt=STTConfig(),
        llm=LLMConfig(
            provider="openai",
            model="gpt-4",
            # Note: Tests will fail if API key not set, but that's expected
        ),
        tts=TTSConfig(),
        safety=SafetyConfig(),
        paths=PathsConfig(),
    )


def test_parse_actions_create_note():
    """Test parsing create_note action from JSON"""
    service = BrainService(create_test_config())
    
    response_json = {
        "actions": [{
            "action_type": "create_note",
            "create_note": {
                "title": "Test Note",
                "content": "This is a test"
            },
            "confidence": 0.9,
            "reasoning": "User wants to save information"
        }]
    }
    
    actions = service._parse_actions(response_json)
    assert len(actions) == 1
    assert actions[0].action_type == "create_note"
    assert actions[0].create_note is not None
    assert actions[0].create_note.title == "Test Note"


def test_parse_actions_create_task():
    """Test parsing create_task action from JSON"""
    service = BrainService(create_test_config())
    
    response_json = {
        "actions": [{
            "action_type": "create_task",
            "create_task": {
                "title": "Review PR",
                "description": "Review pull request #123",
                "priority": "high"
            }
        }]
    }
    
    actions = service._parse_actions(response_json)
    assert len(actions) == 1
    assert actions[0].action_type == "create_task"
    assert actions[0].create_task.title == "Review PR"
    assert actions[0].create_task.priority == "high"


def test_parse_actions_conversation():
    """Test parsing conversation action from JSON"""
    service = BrainService(create_test_config())
    
    response_json = {
        "actions": [{
            "action_type": "conversation",
            "conversation": "Hello! How can I help you?"
        }]
    }
    
    actions = service._parse_actions(response_json)
    assert len(actions) == 1
    assert actions[0].action_type == "conversation"
    assert actions[0].conversation == "Hello! How can I help you?"


def test_extract_json_from_markdown():
    """Test extracting JSON from markdown code blocks"""
    service = BrainService(create_test_config())
    
    text = """
    Here's the response:
    ```json
    {
        "actions": [{
            "action_type": "conversation",
            "conversation": "Hello"
        }]
    }
    ```
    """
    
    json_data = service._extract_json(text)
    assert "actions" in json_data
    assert len(json_data["actions"]) == 1


def test_extract_json_direct():
    """Test extracting JSON directly"""
    service = BrainService(create_test_config())
    
    text = '{"actions": [{"action_type": "conversation", "conversation": "Hi"}]}'
    
    json_data = service._extract_json(text)
    assert "actions" in json_data



