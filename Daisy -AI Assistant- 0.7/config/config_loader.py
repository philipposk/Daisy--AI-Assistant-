"""
Configuration loader with support for JSON and YAML
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# Fix #18: lazy yaml import — real fallback if PyYAML is not installed.
try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    yaml = None
    _YAML_AVAILABLE = False

# Import defaults - handle both package and script execution
try:
    from .defaults import DEFAULT_CONFIG
except ImportError:
    from config.defaults import DEFAULT_CONFIG


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix #19: recursive merge so nested dicts (stt/llm/tts/safety/paths) compose
    cleanly. Values from `overlay` win, but missing keys keep their base value.
    """
    out: Dict[str, Any] = {}
    for key in set(base) | set(overlay):
        if key in base and key in overlay:
            if isinstance(base[key], dict) and isinstance(overlay[key], dict):
                out[key] = _deep_merge(base[key], overlay[key])
            else:
                out[key] = overlay[key]
        elif key in overlay:
            out[key] = overlay[key]
        else:
            out[key] = base[key]
    return out


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
    provider: str = "openai"  # openai, groq, local_http (ollama), anthropic (0.8)
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None  # Reserved for 0.8 Anthropic provider
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
    # Fix #7 companion: Piper TTS settings used by VoiceService._tts_piper.
    piper_binary: Optional[str] = None       # default resolves to `piper` on PATH
    piper_model: Optional[str] = None        # path to .onnx voice model


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
        """Create Config from dictionary, tolerating unknown keys."""
        config = cls()

        def _safe(cls_, payload):
            allowed = {f for f in cls_.__dataclass_fields__}
            return cls_(**{k: v for k, v in payload.items() if k in allowed})

        if "stt" in data:
            config.stt = _safe(STTConfig, data["stt"])
        if "llm" in data:
            config.llm = _safe(LLMConfig, data["llm"])
        if "tts" in data:
            config.tts = _safe(TTSConfig, data["tts"])
        if "safety" in data:
            config.safety = _safe(SafetyConfig, data["safety"])
        if "paths" in data:
            config.paths = _safe(PathsConfig, data["paths"])
        
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


def _load_config_file(config_path: Path) -> Dict[str, Any]:
    """Read JSON or YAML config file. Fix #18: clean YAML / JSON dispatch."""
    suffix = config_path.suffix.lower()
    with open(config_path, "r") as f:
        if suffix in (".yaml", ".yml"):
            if not _YAML_AVAILABLE:
                raise RuntimeError(
                    f"Config file {config_path} is YAML but PyYAML is not installed. "
                    "pip install PyYAML or convert to JSON."
                )
            return yaml.safe_load(f) or {}
        return json.load(f)


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or environment."""
    global _global_config

    if config_path is None:
        config_path = Path.home() / ".daisy" / "config.yaml"

    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Start with defaults
    merged: Dict[str, Any] = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy

    # 2. Overlay file data (deep-merged so nested keys compose — fix #19)
    if config_path.exists():
        file_data = _load_config_file(config_path)
        if file_data:
            merged = _deep_merge(merged, file_data)

    # 3. Overlay environment variables (fix #20: added ANTHROPIC + GOOGLE)
    env_overlay: Dict[str, Any] = {}
    if "OPENAI_API_KEY" in os.environ:
        env_overlay.setdefault("llm", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
        env_overlay.setdefault("stt", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
        env_overlay.setdefault("tts", {})["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    if "GROQ_API_KEY" in os.environ:
        env_overlay.setdefault("llm", {})["groq_api_key"] = os.environ["GROQ_API_KEY"]
    if "ANTHROPIC_API_KEY" in os.environ:
        env_overlay.setdefault("llm", {})["anthropic_api_key"] = os.environ["ANTHROPIC_API_KEY"]
    if "GOOGLE_API_KEY" in os.environ:
        env_overlay.setdefault("stt", {})["google_api_key"] = os.environ["GOOGLE_API_KEY"]

    if env_overlay:
        merged = _deep_merge(merged, env_overlay)

    config = Config.from_dict(merged)
    _global_config = config

    # Save config if it didn't exist (so the user has a template to edit)
    if not config_path.exists():
        try:
            save_config(config, config_path)
        except Exception:
            # Saving a template is best-effort; don't fail load
            pass

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
            for api_key_field in ("openai_api_key", "groq_api_key", "google_api_key", "anthropic_api_key"):
                if api_key_field in config_dict[key]:
                    config_dict[key][api_key_field] = None

    suffix = config_path.suffix.lower()
    with open(config_path, "w") as f:
        if suffix in (".yaml", ".yml") and _YAML_AVAILABLE:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        else:
            # Either explicit .json, or YAML requested with no PyYAML installed.
            json.dump(config_dict, f, indent=2)

