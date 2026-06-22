"""
Tests for Anthropic provider + provider-chain (0.8).
"""
from unittest.mock import MagicMock, patch

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from services.brain_service import BrainService
from schemas import TranscriptionResult


def _cfg(provider: str = "anthropic", **llm_kw) -> Config:
    return Config(
        stt=STTConfig(), llm=LLMConfig(provider=provider, **llm_kw),
        tts=TTSConfig(), safety=SafetyConfig(), paths=PathsConfig(),
    )


def test_anthropic_provider_chain_includes_anthropic_when_configured():
    cfg = _cfg(provider="anthropic", anthropic_api_key="sk-fake")
    with patch("services.brain_service.anthropic") as mock_module:
        mock_module.Anthropic.return_value = MagicMock()
        svc = BrainService(cfg)
        chain = svc._build_provider_chain()
        assert chain[0] == "anthropic"


def test_anthropic_call_returns_concatenated_text():
    cfg = _cfg(provider="anthropic", anthropic_api_key="sk-fake")
    with patch("services.brain_service.anthropic") as mock_module:
        fake_client = MagicMock()
        # Mock message.content list of blocks with .text
        block_a = MagicMock(); block_a.text = "{\"actions\": "
        block_b = MagicMock(); block_b.text = "[{\"action_type\":\"conversation\",\"conversation\":\"hi\"}]}"
        fake_resp = MagicMock(); fake_resp.content = [block_a, block_b]
        fake_client.messages.create.return_value = fake_resp
        mock_module.Anthropic.return_value = fake_client

        svc = BrainService(cfg)
        out = svc._call_anthropic("test")
        assert "conversation" in out
        # Verify system block carries cache_control
        kwargs = fake_client.messages.create.call_args.kwargs
        sys_blocks = kwargs["system"]
        assert sys_blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_default_model_used_when_user_picks_gpt4():
    cfg = _cfg(provider="anthropic", anthropic_api_key="sk-fake", model="gpt-4")
    with patch("services.brain_service.anthropic") as mock_module:
        fake_client = MagicMock()
        fake_resp = MagicMock(); fake_resp.content = [MagicMock(text="{}")]
        fake_client.messages.create.return_value = fake_resp
        mock_module.Anthropic.return_value = fake_client
        svc = BrainService(cfg)
        svc._call_anthropic("test")
        kwargs = fake_client.messages.create.call_args.kwargs
        assert "claude" in kwargs["model"]


def test_provider_chain_falls_back_when_primary_fails():
    cfg = _cfg(provider="anthropic", anthropic_api_key="sk-fake")
    cfg.llm.openai_api_key = "sk-openai"  # so openai is "available" for fallback
    with patch("services.brain_service.anthropic") as anth_mod, \
         patch("services.brain_service.OpenAI") as openai_cls:
        anth_client = MagicMock()
        anth_client.messages.create.side_effect = RuntimeError("rate limited")
        anth_mod.Anthropic.return_value = anth_client

        openai_client = MagicMock()
        openai_resp = MagicMock()
        openai_resp.choices = [MagicMock(message=MagicMock(content='{"actions":[{"action_type":"conversation","conversation":"hi"}]}'))]
        openai_client.chat.completions.create.return_value = openai_resp
        openai_cls.return_value = openai_client

        svc = BrainService(cfg)
        intent = svc.plan_actions(TranscriptionResult(text="hi"))
        # openai responded → at least one action
        assert intent.actions
        assert intent.actions[0].action_type == "conversation"


def test_current_system_prompt_contains_date():
    from services.brain_service import _current_system_prompt
    text = _current_system_prompt()
    assert "CURRENT_DATE" in text
    # ISO-ish
    assert "T" in text
