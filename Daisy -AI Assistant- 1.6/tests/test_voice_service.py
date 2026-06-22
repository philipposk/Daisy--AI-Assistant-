"""
Tests for VoiceService (0.7 fixes #5, #7, #8, #21).

Notes: avoids any real STT/TTS network calls; uses subprocess monkeypatches
to verify the shape of the Piper / `say` invocations.
"""
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from config import Config, STTConfig, LLMConfig, TTSConfig, SafetyConfig, PathsConfig
from services.voice_service import VoiceService


def _config(**tts_overrides) -> Config:
    return Config(
        stt=STTConfig(),
        llm=LLMConfig(),
        tts=TTSConfig(**tts_overrides),
        safety=SafetyConfig(),
        paths=PathsConfig(),
    )


def test_tts_piper_requires_model():
    """Fix #7: without a model path, _tts_piper raises a useful error (not NotImplementedError)."""
    service = VoiceService(_config(provider="piper"))
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out = Path(tf.name)
    try:
        try:
            service._tts_piper("hello", out)
        except RuntimeError as e:
            assert "piper_model" in str(e).lower() or "model" in str(e).lower()
        else:
            raise AssertionError("expected RuntimeError when piper_model missing")
    finally:
        out.unlink(missing_ok=True)


def test_tts_piper_shells_out_with_model():
    """Fix #7: with a model path set, _tts_piper invokes `piper --model ... --output_file ...`."""
    cfg = _config(provider="piper", piper_binary="piper", piper_model="/tmp/voice.onnx")
    service = VoiceService(cfg)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out = Path(tf.name)
    out.unlink()  # We don't actually want the file to exist when piper "runs"

    fake_completed = MagicMock(returncode=0, stdout="", stderr="")
    with patch("services.voice_service.subprocess.run", return_value=fake_completed) as run:
        # Pre-create a stub output so the rename/replace step finds something.
        with patch("services.voice_service.tempfile.NamedTemporaryFile") as ntf:
            tmp = MagicMock()
            stub_path = Path(tempfile.gettempdir()) / "stub_piper_out.wav"
            stub_path.write_bytes(b"riffwav")
            tmp.name = str(stub_path)
            ntf.return_value = tmp
            try:
                result = service._tts_piper("hello", out)
            finally:
                stub_path.unlink(missing_ok=True)
                out.unlink(missing_ok=True)

        assert run.called
        args = run.call_args[0][0]
        assert args[0] == "piper"
        assert "--model" in args
        assert "/tmp/voice.onnx" in args
        assert "--output_file" in args


def test_system_tts_voice_from_config():
    """Fix #8: macOS `say` uses config voice (or its mapping), not hardcoded 'Victoria'."""
    cfg = _config(provider="system", voice="Daniel")  # 'Daniel' is a real `say` voice
    service = VoiceService(cfg)

    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tf:
        out = Path(tf.name)
    out.unlink()

    fake_completed = MagicMock(returncode=0)
    with patch("services.voice_service.subprocess.run", return_value=fake_completed) as run:
        try:
            service._tts_system("hi", out)
        except Exception:
            pass  # rename/move logic may error after mock; we only care about argv

        # Find the `say` invocation
        say_calls = [c for c in run.call_args_list if c.args and c.args[0] and c.args[0][0] == "say"]
        assert say_calls, "expected a `say` subprocess invocation"
        argv = say_calls[0].args[0]
        assert "-v" in argv
        v_idx = argv.index("-v")
        assert argv[v_idx + 1] == "Daniel"


def test_separate_stt_and_tts_keys():
    """Fix #5: an explicit tts.openai_api_key is honoured separately from stt.openai_api_key."""
    cfg = Config(
        stt=STTConfig(openai_api_key="STT_KEY"),
        llm=LLMConfig(),
        tts=TTSConfig(openai_api_key="TTS_KEY"),
        safety=SafetyConfig(),
        paths=PathsConfig(),
    )
    with patch("services.voice_service.OpenAI") as openai_mock:
        VoiceService(cfg)
        # Two distinct constructions: one with each key
        keys_used = {call.kwargs.get("api_key") for call in openai_mock.call_args_list}
        assert {"STT_KEY", "TTS_KEY"}.issubset(keys_used)


def test_play_audio_records_playback_handle():
    """Fix #21: play_audio stores a Popen handle (so 0.8 can interrupt)."""
    cfg = _config()
    service = VoiceService(cfg)

    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0
    fake_proc.poll.return_value = None  # "still running" so stop_playback() actually terminates
    with patch("services.voice_service.subprocess.Popen", return_value=fake_proc):
        service.play_audio(Path("/dev/null"), wait=False)
        assert service.current_playback is fake_proc
        service.stop_playback()
        fake_proc.terminate.assert_called_once()
