"""
Barge-in (0.8).

Runs a VAD listener in a background thread during TTS playback. When voice
activity exceeds a threshold, the playback handle (`VoiceService.current_playback`)
is terminated and any pending TTS is cancelled. Voice loop picks up the next
turn immediately.

Two VAD strategies, picked at runtime:
- WebRTC VAD (`pip install webrtcvad`) — fast, no model.
- Energy threshold fallback — cheap, no dep. Less reliable but works everywhere.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from utils import get_logger

logger = get_logger("barge_in")


class BargeInWatcher:
    """
    Background watcher. `start()` it just before playing TTS; `stop()` after.
    If speech is detected during the window, it calls `voice_service.stop_playback()`
    and sets `triggered=True`.
    """

    def __init__(self, voice_service, sensitivity: int = 2, frame_ms: int = 30,
                 sample_rate: int = 16000, min_voiced_ms: int = 200):
        self.voice = voice_service
        self.sensitivity = max(0, min(3, sensitivity))  # webrtcvad: 0=permissive, 3=aggressive
        self.frame_ms = frame_ms
        self.sample_rate = sample_rate
        self.min_voiced_ms = min_voiced_ms

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.triggered: bool = False

    # ----------------- public API -----------------

    def start(self) -> None:
        self.triggered = False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    # ----------------- internals -----------------

    def _run(self) -> None:  # pragma: no cover - hardware-dependent
        try:
            self._run_webrtc()
        except Exception as e:
            logger.warning(f"WebRTC VAD unavailable ({e}); falling back to energy threshold.")
            try:
                self._run_energy()
            except Exception as e2:
                logger.warning(f"Energy VAD failed too: {e2}")

    def _run_webrtc(self) -> None:  # pragma: no cover
        import webrtcvad  # type: ignore
        import pyaudio  # type: ignore

        vad = webrtcvad.Vad(self.sensitivity)
        pa = pyaudio.PyAudio()
        frames_per_buffer = int(self.sample_rate * self.frame_ms / 1000)
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=self.sample_rate,
            input=True, frames_per_buffer=frames_per_buffer,
        )
        try:
            voiced_ms = 0
            while not self._stop_event.is_set():
                frame = stream.read(frames_per_buffer, exception_on_overflow=False)
                if vad.is_speech(frame, self.sample_rate):
                    voiced_ms += self.frame_ms
                    if voiced_ms >= self.min_voiced_ms:
                        self._fire()
                        return
                else:
                    voiced_ms = max(0, voiced_ms - self.frame_ms)
        finally:
            try:
                stream.stop_stream()
                stream.close()
            finally:
                pa.terminate()

    def _run_energy(self) -> None:  # pragma: no cover
        import audioop
        import pyaudio  # type: ignore

        pa = pyaudio.PyAudio()
        frames_per_buffer = int(self.sample_rate * self.frame_ms / 1000)
        stream = pa.open(
            format=pyaudio.paInt16, channels=1, rate=self.sample_rate,
            input=True, frames_per_buffer=frames_per_buffer,
        )
        try:
            voiced_ms = 0
            threshold = 1500  # rms — tweak via config later
            while not self._stop_event.is_set():
                frame = stream.read(frames_per_buffer, exception_on_overflow=False)
                rms = audioop.rms(frame, 2)
                if rms > threshold:
                    voiced_ms += self.frame_ms
                    if voiced_ms >= self.min_voiced_ms:
                        self._fire()
                        return
                else:
                    voiced_ms = max(0, voiced_ms - self.frame_ms)
        finally:
            try:
                stream.stop_stream()
                stream.close()
            finally:
                pa.terminate()

    def _fire(self) -> None:
        self.triggered = True
        try:
            self.voice.stop_playback()
        except Exception:
            pass
        logger.info("Barge-in triggered; TTS interrupted.")


def speak_with_barge_in(voice_service, text: str) -> bool:
    """
    Convenience helper. Generates TTS, plays it while watching for barge-in.
    Returns True if completed normally, False if interrupted.
    """
    audio_path = voice_service.text_to_speech(text)
    watcher = BargeInWatcher(voice_service)
    watcher.start()
    try:
        voice_service.play_audio(audio_path, wait=True)
    finally:
        watcher.stop()
        try:
            audio_path.unlink()
        except Exception:
            pass
    return not watcher.triggered
