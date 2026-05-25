"""
Configuration loader with support for JSON and YAML
"""
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
# Import defaults - handle both package and script execution
try:
    from .defaults import DEFAULT_CONFIG
except ImportError:
    from config.defaults import DEFAULT_CONFIG


@dataclass
class STTConfig:
    """Speech-to-Text configuration"""
    provider: str = "openai"  # openai, google, local_http
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    local_http_url: Optional[str] = None  # http://localhost:8000/transcribe
    fallback_enabled: bool = True


@dataclass
class LLMConfig:
    """LLM configuration"""
    provider: str = "openai"  # openai, groq, local_http (ollama)
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    model: str = "gpt-4"
    local_http_url: Optional[str] = None  # http://localhost:11434/api/generate
    temperature: float = 0.7
    max_tokens: int = 1000
    fallback_enabled: bool = True


@dataclass
class TTSConfig:
    """Text-to-Speech configuration"""
    provider: str = "openai"  # openai, piper, local_http
    voice: str = "nova"
    openai_api_key: Optional[str] = None
    local_http_url: Optional[str] = None


@dataclass
class SafetyConfig:
    """Safety and permission configuration"""
    whitelisted_commands: List[str] = field(default_factory=list)
    whitelisted_directories: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf", "del /f", "format", "fdisk", "dd if="
    ])
    require_confirmation_for: List[str] = field(default_factory=lambda: [
        "rm", "del", "mv", "move", "delete"
    ])
    block_network_commands: bool = True
    block_system_modifying_commands: bool = True


@dataclass
class PathsConfig:
    """Paths configuration"""
    notes_directory: str = "~/.daisy/notes"
    tasks_file: str = "~/.daisy/tasks.md"
    reminders_file: str = "~/.daisy/reminders.json"
    audit_log: str = "~/.daisy/audit.log"
    conversations_directory: str = "~/.daisy/conversations"
    database_path: str = "~/.daisy/daisy.db"


@dataclass
class Config:
    """Main configuration class"""
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    
    # General settings
    save_conversations: bool = True
    max_conversation_history: int = 50
    enable_audit_logging: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary"""
        config = cls()
        
        if "stt" in data:
            config.stt = STTConfig(**data["stt"])
        if "llm" in data:
            config.llm = LLMConfig(**data["llm"])
        if "tts" in data:
            config.tts = TTSConfig(**data["tts"])
        if "safety" in data:
            config.safety = SafetyConfig(**data["safety"])
        if "paths" in data:
            config.paths = PathsConfig(**data["paths"])
        
        # General settings
        if "save_conversations" in data:
            config.save_conversations = data["save_conversations"]
        if "max_conversation_history" in data:
            config.max_conversation_history = data["max_conversation_history"]
        if "enable_audit_logging" in data:
            config.enable_audit_logging = data["enable_audit_logging"]
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary"""
        return {
            "stt": self.stt.__dict__,
            "llm": self.llm.__dict__,
            "tts": self.tts.__dict__,
            "safety": self.safety.__dict__,
            "paths": self.paths.__dict__,
            "save_conversations": self.save_conversations,
            "max_conversation_history": self.max_conversation_history,
            "enable_audit_logging": self.enable_audit_logging,
        }


_global_config: Optional[Config] = None


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or environment"""
    global _global_config
    
    if config_path is None:
        config_path = Path.home() / ".daisy" / "config.yaml"
    
    config_path = Path(config_path).expanduser()
    
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Start with defaults
    config_dict = DEFAULT_CONFIG.copy()
    
    # Load from file if it exists
    if config_path.exists():
        with open(config_path, 'r') as f:
            if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
                try:
                    file_data = yaml.safe_load(f) or {}
                except ImportError:
                    # Fallback to JSON if YAML not available
                    file_data = json.load(f)
            else:
                file_data = json.load(f)
            config_dict.update(file_data)
    
    # Override with environment variables
    import os
    if "OPENAI_API_KEY" in os.environ:
        config_dict.setdefault("llm", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
        config_dict.setdefault("stt", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
        config_dict.setdefault("tts", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    if "GROQ_API_KEY" in os.environ:
        config_dict.setdefault("llm", {})["groq_api_key"] = os.environ["GROQ_API_KEY"]
    
    # Merge nested configs properly
    merged = DEFAULT_CONFIG.copy()
    merged.update(config_dict)
    for key in ["stt", "llm", "tts", "safety", "paths"]:
        if key in config_dict:
            merged[key] = {**merged.get(key, {}), **config_dict[key]}
    
    config = Config.from_dict(merged)
    _global_config = config
    
    # Save config if it didn't exist
    if not config_path.exists():
        save_config(config, config_path)
    
    return config


def get_config() -> Config:
    """Get the global configuration"""
    global _global_config
    if _global_config is None:
        _global_config = load_config()
    return _global_config


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to file"""
    if config_path is None:
        config_path = Path.home() / ".daisy" / "config.yaml"
    
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_dict = config.to_dict()
    
    # Remove API keys from saved config (they should come from env)
    for key in ["stt", "llm", "tts"]:
        if key in config_dict:
            for api_key_field in ["openai_api_key", "groq_api_key", "google_api_key"]:
                if api_key_field in config_dict[key]:
                    config_dict[key][api_key_field] = None
    
    with open(config_path, 'w') as f:
        if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
            try:
                yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            except ImportError:
                json.dump(config_dict, f, indent=2)
        else:
            json.dump(config_dict, f, indent=2)

