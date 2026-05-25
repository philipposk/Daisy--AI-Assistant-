"""
Default configuration values
"""
DEFAULT_CONFIG = {
    "stt": {
        "provider": "openai",
        "openai_api_key": None,
        "google_api_key": None,
        "local_http_url": None,
        "fallback_enabled": True,
    },
    "llm": {
        "provider": "openai",
        "openai_api_key": None,
        "groq_api_key": None,
        "model": "gpt-4",
        "local_http_url": None,
        "temperature": 0.7,
        "max_tokens": 1000,
        "fallback_enabled": True,
    },
    "tts": {
        "provider": "openai",
        "voice": "nova",
        "openai_api_key": None,
        "local_http_url": None,
    },
    "safety": {
        "whitelisted_commands": [],
        "whitelisted_directories": [],
        "blocked_commands": [
            "rm -rf",
            "del /f",
            "format",
            "fdisk",
            "dd if=",
        ],
        "require_confirmation_for": [
            "rm",
            "del",
            "mv",
            "move",
            "delete",
        ],
        "block_network_commands": True,
        "block_system_modifying_commands": True,
    },
    "paths": {
        "notes_directory": "~/.daisy/notes",
        "tasks_file": "~/.daisy/tasks.md",
        "reminders_file": "~/.daisy/reminders.json",
        "audit_log": "~/.daisy/audit.log",
        "conversations_directory": "~/.daisy/conversations",
        "database_path": "~/.daisy/daisy.db",
    },
    "save_conversations": True,
    "max_conversation_history": 50,
    "enable_audit_logging": True,
}

