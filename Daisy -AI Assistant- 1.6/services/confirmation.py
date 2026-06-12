"""
Confirmation provider (0.8).

Replaces 0.7's "log and skip + failed ActionResult" behaviour with a real
yes/no prompt. Two backends:

- CLIConfirmation: synchronous y/N prompt on stdin.
- VoiceConfirmation: TTS asks the user, listens for yes/no/cancel.
- AutoApproveConfirmation / AutoRejectConfirmation: deterministic backends
  for tests and headless contexts.

`build_confirmation_provider(config, voice_service)` is the factory.
"""
from __future__ import annotations

import sys
import time
from typing import Optional, Protocol

from schemas import AssistantAction
from utils import get_logger

logger = get_logger("confirmation")


class ConfirmationProvider(Protocol):
    def confirm(self, action: AssistantAction, prompt: str) -> bool:
        ...


# ----------------- backends -----------------


class AutoApproveConfirmation:
    """Always says yes. Use for tests or `--yes` CLI mode."""

    def confirm(self, action: AssistantAction, prompt: str) -> bool:  # noqa: ARG002
        return True


class AutoRejectConfirmation:
    """Always says no. Use for headless contexts where prompts can't surface."""

    def confirm(self, action: AssistantAction, prompt: str) -> bool:  # noqa: ARG002
        return False


class CLIConfirmation:
    """Synchronous y/N prompt on stdin. Falls through to reject if stdin closed."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout_seconds = timeout_seconds

    def confirm(self, action: AssistantAction, prompt: str) -> bool:
        if not sys.stdin.isatty():
            logger.warning("stdin not a TTY; rejecting confirmation by default.")
            return False
        try:
            sys.stdout.write(f"\n{prompt} [y/N]: ")
            sys.stdout.flush()
            line = sys.stdin.readline().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return line in ("y", "yes")


class VoiceConfirmation:
    """
    TTS asks "should I run …?"; listens for next short utterance; parses yes/no.
    """

    YES_WORDS = {"yes", "yeah", "yep", "yup", "ok", "okay", "go", "do it", "sure", "confirm"}
    NO_WORDS = {"no", "nope", "stop", "cancel", "abort", "don't", "do not", "nah"}

    def __init__(self, voice_service, listen_seconds: float = 5.0):
        self.voice = voice_service
        self.listen_seconds = listen_seconds

    def confirm(self, action: AssistantAction, prompt: str) -> bool:  # pragma: no cover - hardware
        import speech_recognition as sr
        import tempfile
        from pathlib import Path

        try:
            audio_path = self.voice.text_to_speech(prompt + " Say yes or no.")
            self.voice.play_audio(audio_path, wait=True)
            try:
                audio_path.unlink()
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"VoiceConfirmation TTS failed: {e}; falling back to CLI.")
            return CLIConfirmation().confirm(action, prompt)

        recognizer = sr.Recognizer()
        try:
            microphone = sr.Microphone()
        except Exception:
            logger.warning("Microphone unavailable; falling back to CLI.")
            return CLIConfirmation().confirm(action, prompt)

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = recognizer.listen(source, timeout=self.listen_seconds, phrase_time_limit=self.listen_seconds)
            except Exception:
                return False

        tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tf.close()
        tmp = Path(tf.name)
        try:
            tmp.write_bytes(audio.get_wav_data())
            transcript = self.voice.transcribe_audio_file(tmp)
        finally:
            try:
                tmp.unlink()
            except Exception:
                pass

        text = (transcript.text or "").lower().strip()
        logger.info(f"VoiceConfirmation heard: {text!r}")
        if any(w in text for w in self.NO_WORDS):
            return False
        if any(w in text for w in self.YES_WORDS):
            return True
        return False  # ambiguous → reject


# ----------------- factory -----------------


def build_confirmation_provider(config, voice_service=None) -> ConfirmationProvider:
    mode = (getattr(config.confirmation, "mode", "cli") or "cli").lower()
    timeout = float(getattr(config.confirmation, "timeout_seconds", 30.0) or 30.0)

    if mode == "auto_approve":
        return AutoApproveConfirmation()
    if mode == "auto_reject":
        return AutoRejectConfirmation()
    if mode == "voice":
        if voice_service is None:
            logger.warning("voice confirmation requested without VoiceService; using CLI.")
            return CLIConfirmation(timeout_seconds=timeout)
        return VoiceConfirmation(voice_service)
    # default: cli
    return CLIConfirmation(timeout_seconds=timeout)


def describe_action(action: AssistantAction) -> str:
    """Human-readable summary used in the prompt."""
    if action.action_type == "run_command" and action.run_command:
        wd = action.run_command.working_directory or "cwd"
        return f"Run command `{action.run_command.command}` (in {wd})?"
    if action.action_type == "create_note" and action.create_note:
        return f"Create note `{action.create_note.title}`?"
    if action.action_type == "create_task" and action.create_task:
        return f"Create task `{action.create_task.title}`?"
    if action.action_type == "create_reminder" and action.create_reminder:
        return f"Create reminder `{action.create_reminder.message}`?"
    return f"Perform action `{action.action_type}`?"
