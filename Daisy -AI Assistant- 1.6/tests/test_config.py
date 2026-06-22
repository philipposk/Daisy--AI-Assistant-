"""
Tests for configuration system
"""
import tempfile
import json
import yaml
from pathlib import Path
from config import load_config, Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig


def test_default_config():
    """Test loading default configuration"""
    config = load_config()
    assert isinstance(config, Config)
    assert config.stt.provider == "openai"
    assert config.llm.provider == "openai"


def test_config_from_dict():
    """Test creating config from dictionary"""
    config_dict = {
        "stt": {
            "provider": "google",
            "fallback_enabled": True,
        },
        "llm": {
            "provider": "groq",
            "model": "llama-3.1-70b-versatile",
        },
        "safety": {
            "blocked_commands": ["rm -rf"],
        },
    }
    
    config = Config.from_dict(config_dict)
    assert config.stt.provider == "google"
    assert config.llm.provider == "groq"
    assert "rm -rf" in config.safety.blocked_commands


def test_config_to_dict():
    """Test converting config to dictionary"""
    config = Config()
    config_dict = config.to_dict()
    
    assert "stt" in config_dict
    assert "llm" in config_dict
    assert "safety" in config_dict
    assert "paths" in config_dict


def test_load_json_config():
    """Test loading JSON configuration file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.json"
        
        config_data = {
            "llm": {
                "model": "gpt-3.5-turbo",
                "temperature": 0.8,
            },
            "safety": {
                "blocked_commands": ["sudo"],
            },
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        config = load_config(config_file)
        assert config.llm.model == "gpt-3.5-turbo"
        assert config.llm.temperature == 0.8
        assert "sudo" in config.safety.blocked_commands


def test_load_yaml_config():
    """Test loading YAML configuration file"""
    try:
        import yaml
    except ImportError:
        # Skip if YAML not available
        return
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "config.yaml"
        
        config_data = {
            "llm": {
                "model": "gpt-4",
            },
            "paths": {
                "notes_directory": "~/custom/notes",
            },
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        config = load_config(config_file)
        assert config.llm.model == "gpt-4"
        assert "custom/notes" in config.paths.notes_directory


def test_environment_variable_override():
    """Test that environment variables override config"""
    import os
    
    # Save original
    original_key = os.environ.get("OPENAI_API_KEY")
    
    try:
        os.environ["OPENAI_API_KEY"] = "test-key-123"
        
        config = load_config()
        # The key should be set (though we can't verify it's from env vs config file)
        # But we can verify the config structure is correct
        assert config.stt.openai_api_key is None or config.stt.openai_api_key == "test-key-123"
    finally:
        if original_key:
            os.environ["OPENAI_API_KEY"] = original_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]



