"""
Wake-word detection (0.8).

Two backends:
- OpenWakeWordBackend: uses the `openwakeword` pip package + a custom .tflite/.onnx
  model trained for "daisy". Offline, low CPU. Preferred.
- WhisperPollBackend: cheap fallback that records short audio chunks and runs them
  through the existing VoiceService STT, returning True when the transcript contains
  the wake word. Works with no extra dependency, but costs an STT call per chunk.

Configuration (in `config.yaml` under a new `wake_word` section):

    wake_word:
      enabled: true
      provider: "openwakeword"        # or "whisper_poll" or "disabled"
      keyword: "daisy"
      openwakeword_model: "~/.daisy/wake/daisy.onnx"
      chunk_seconds: 1.5              # whisper_poll only
      cooldown_seconds: 3.0           # don't re-trigger immediately
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Protocol


class WakeWordBackend(Protocol):
    def listen_once(self) -> bool:
        """Block until wake word detected (True) or backend gives up (False)."""
        ...

    def close(self) -> None:
        ...


class DisabledBackend:
    """No-op backend — wake word detection turned off."""

    def listen_once(self) -> bool:
        return True  # always "detected" so voice_loop runs as classic PTT

    def close(self) -> None:
        pass


class OpenWakeWordBackend:
    """openWakeWord (https://github.com/dscripka/openWakeWord) backend."""

    def __init__(self, model_path: Path, keyword: str = "daisy"):
        try:
            from openwakeword import Model  # type: ignore
            import pyaudio  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "OpenWakeWordBackend needs `pip install openwakeword pyaudio`."
            ) from e

        self.keyword = keyword
        self.model_path = Path(model_path).expanduser()
        if not self.model_path.exists():
            raise RuntimeError(
                f"openWakeWord model not found at {self.model_path}. "
                f"Train one via the project's Colab and set wake_word.openwakeword_model in config."
            )
        self._Model = Model
        self._pyaudio_mod = pyaudio
        self._model = Model(wakeword_models=[str(self.model_path)])
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, frames_per_buffer=1280,
        )

    def listen_once(self) -> bool:  # pragma: no cover - hardware-dependent
        import numpy as np  # local import: numpy is brought in by openwakeword
        while True:
            audio = np.frombuffer(self._stream.read(1280, exception_on_overflow=False), dtype=np.int16)
            prediction = self._model.predict(audio)
            for _, score in prediction.items():
                if score > 0.5:
                    return True

    def close(self) -> None:  # pragma: no cover
        try:
            self._stream.stop_stream()
            self._stream.close()
        finally:
            self._pa.terminate()


class WhisperPollBackend:
    """
    Cheap fallback. Record `chunk_seconds` of audio, transcribe, look for keyword.
    Loops until found. Uses the existing VoiceService for STT so no new deps.
    """

    def __init__(self, voice_service, keyword: str = "daisy",
                 chunk_seconds: float = 1.5, cooldown_seconds: float = 3.0):
        self.voice = voice_service
        self.keyword = keyword.lower()
        self.chunk_seconds = chunk_seconds
        self.cooldown_seconds = cooldown_seconds
        self._last_trigger = 0.0

    def listen_once(self) -> bool:
        import speech_recognition as sr  # already a project dep
        import tempfile

        recognizer = sr.Recognizer()
        try:
            microphone = sr.Microphone()
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"Microphone unavailable for wake-word polling: {e}")

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)

        while True:
            with microphone as source:
                try:
                    audio = recognizer.listen(
                        source, timeout=None,
                        phrase_time_limit=self.chunk_seconds,
                    )
                except Exception:  # pragma: no cover
                    continue

            tf = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tf.close()
            tmp = Path(tf.name)
            try:
                tmp.write_bytes(audio.get_wav_data())
                try:
                    transcript = self.voice.transcribe_audio_file(tmp)
                except Exception:
                    continue
                text = (transcript.text or "").lower().strip()
                if self.keyword in text and (time.time() - self._last_trigger) > self.cooldown_seconds:
                    self._last_trigger = time.time()
                    return True
            finally:
                try:
                    tmp.unlink()
                except Exception:
                    pass

    def close(self) -> None:
        pass


def build_wake_word_backend(config, voice_service) -> WakeWordBackend:
    """
    Factory. Reads `config.wake_word` and instantiates the right backend.
    Falls back gracefully if a backend's deps are missing.
    """
    ww = getattr(config, "wake_word", None)
    if ww is None or not getattr(ww, "enabled", False):
        return DisabledBackend()

    provider = (getattr(ww, "provider", "openwakeword") or "openwakeword").lower()

    if provider == "disabled":
        return DisabledBackend()

    if provider == "openwakeword":
        model = getattr(ww, "openwakeword_model", None)
        if not model:
            # No model configured → silently downgrade to whisper_poll.
            provider = "whisper_poll"
        else:
            try:
                return OpenWakeWordBackend(
                    model_path=Path(model).expanduser(),
                    keyword=getattr(ww, "keyword", "daisy") or "daisy",
                )
            except RuntimeError as e:
                # openwakeword not installed or model missing → fallback
                from utils import get_logger
                get_logger("wake_word").warning(f"{e}; falling back to whisper-poll wake word.")
                provider = "whisper_poll"

    if provider == "whisper_poll":
        return WhisperPollBackend(
            voice_service=voice_service,
            keyword=getattr(ww, "keyword", "daisy") or "daisy",
            chunk_seconds=float(getattr(ww, "chunk_seconds", 1.5) or 1.5),
            cooldown_seconds=float(getattr(ww, "cooldown_seconds", 3.0) or 3.0),
        )

    return DisabledBackend()
