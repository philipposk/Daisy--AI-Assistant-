"""
Tests for wake-word backend factory (0.8). Hardware-dependent backends are
mocked / skipped — only logic paths are exercised.
"""
from unittest.mock import MagicMock

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig, WakeWordConfig
from services.wake_word import build_wake_word_backend, DisabledBackend, WhisperPollBackend


def _cfg(**ww_kw) -> Config:
    return Config(
        stt=STTConfig(), llm=LLMConfig(), tts=TTSConfig(),
        safety=SafetyConfig(), paths=PathsConfig(),
        wake_word=WakeWordConfig(**ww_kw),
    )


def test_disabled_when_flag_false():
    cfg = _cfg(enabled=False)
    backend = build_wake_word_backend(cfg, voice_service=MagicMock())
    assert isinstance(backend, DisabledBackend)


def test_explicit_disabled_provider():
    cfg = _cfg(enabled=True, provider="disabled")
    backend = build_wake_word_backend(cfg, voice_service=MagicMock())
    assert isinstance(backend, DisabledBackend)


def test_openwakeword_missing_model_downgrades_to_whisper_poll():
    cfg = _cfg(enabled=True, provider="openwakeword", openwakeword_model=None)
    backend = build_wake_word_backend(cfg, voice_service=MagicMock())
    assert isinstance(backend, WhisperPollBackend)


def test_whisper_poll_explicit():
    cfg = _cfg(enabled=True, provider="whisper_poll", keyword="daisy",
               chunk_seconds=2.0, cooldown_seconds=4.0)
    backend = build_wake_word_backend(cfg, voice_service=MagicMock())
    assert isinstance(backend, WhisperPollBackend)
    assert backend.keyword == "daisy"
    assert backend.chunk_seconds == 2.0
    assert backend.cooldown_seconds == 4.0


def test_disabled_listen_once_returns_true():
    """DisabledBackend means PTT mode; listen_once should immediately return True."""
    b = DisabledBackend()
    assert b.listen_once() is True
