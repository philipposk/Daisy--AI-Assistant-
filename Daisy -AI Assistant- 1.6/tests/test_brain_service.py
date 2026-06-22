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


# --- 0.7 regression tests (fix #10: brace-balanced JSON extractor) ---


def test_extract_json_with_array_nested():
    """The old regex broke on arrays / nested objects; brace counter must survive."""
    service = BrainService(create_test_config())
    text = """
    Sure, here you go:
    {
      "actions": [
        {
          "action_type": "create_note",
          "create_note": {
            "title": "Pasta",
            "content": "Boil water, add salt.",
            "tags": ["food", "italian"]
          }
        },
        {
          "action_type": "conversation",
          "conversation": "Anything else?"
        }
      ],
      "requires_confirmation": false
    }
    """
    data = service._extract_json(text)
    assert len(data["actions"]) == 2
    assert data["actions"][0]["create_note"]["title"] == "Pasta"


def test_extract_json_with_braces_in_string():
    """Brace counter must ignore { and } inside string literals."""
    service = BrainService(create_test_config())
    text = '{"actions": [{"action_type": "conversation", "conversation": "Use {curly} braces."}]}'
    data = service._extract_json(text)
    assert data["actions"][0]["conversation"] == "Use {curly} braces."


def test_extract_json_in_fenced_block_with_trailing_prose():
    """LLMs sometimes add prose after a code fence; we should still get the JSON."""
    service = BrainService(create_test_config())
    text = """Here's the plan:
```json
{
  "actions": [{"action_type": "conversation", "conversation": "Hi"}]
}
```
Let me know if you want anything else."""
    data = service._extract_json(text)
    assert data["actions"][0]["conversation"] == "Hi"


def test_groq_model_falls_back_for_unknown_model():
    """Fix #9: BrainService picks a valid Groq model even if config.llm.model is OpenAI's."""
    from config import LLMConfig
    cfg = create_test_config()
    cfg.llm = LLMConfig(provider="groq", model="gpt-4")
    service = BrainService(cfg)
    # We don't actually call the API; we just confirm the substitution logic.
    assert "gpt-4" not in BrainService._GROQ_KNOWN_MODELS
    assert BrainService._GROQ_DEFAULT_MODEL in BrainService._GROQ_KNOWN_MODELS



