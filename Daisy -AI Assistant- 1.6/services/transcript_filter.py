"""
Whisper / STT hallucination filter (0.9).

Whisper-family models invent phantom strings when fed silence or non-speech
audio. They're remarkably consistent — usually one of a short list of
boilerplate phrases ("thanks for watching", "subtitles by ...", etc.).

We drop them. Returns True if the transcript looks real, False if it
looks like a phantom and should be discarded.
"""
from __future__ import annotations

from typing import Optional

# Phantoms seen across whisper.cpp, faster-whisper, OpenAI API. Lower-case.
_PHANTOMS = {
    "thanks for watching",
    "thanks for watching!",
    "thank you for watching",
    "subtitles by the amara.org community",
    "subtitles by the ataraxia.org community",
    "subtitled by",
    "subscribe to my channel",
    "please subscribe",
    "you",            # bare word — common silence hallucination
    ".",
    "...",
    "thank you.",
    "okay.",
    "bye.",
    "music",
    "[music]",
    "(music)",
    "♪",
}

# Tiny "noise" phrases that are technically words but should never pass alone.
_TOO_SHORT_LEN = 2


def is_probably_real(text: Optional[str], confidence: Optional[float] = None,
                     min_confidence: float = 0.0) -> bool:
    """
    Returns True if the transcript looks like real speech, False if it looks
    like a phantom and should be discarded.

    - Empty / whitespace → False.
    - Confidence below `min_confidence` (when supplied) → False.
    - Exact match to a known phantom (case-insensitive) → False.
    - Length < _TOO_SHORT_LEN characters → False.
    """
    if text is None:
        return False
    normalized = text.strip().lower()
    if not normalized:
        return False
    if len(normalized) < _TOO_SHORT_LEN:
        return False
    if confidence is not None and confidence < min_confidence:
        return False
    if normalized in _PHANTOMS:
        return False
    # Also reject phantoms with trailing punctuation: "thanks for watching!"
    stripped = normalized.rstrip(".!? ")
    if stripped in _PHANTOMS:
        return False
    return True


def filter_transcript(text: Optional[str], confidence: Optional[float] = None,
                      min_confidence: float = 0.0) -> Optional[str]:
    """Convenience: returns text if it passes, else None."""
    if is_probably_real(text, confidence, min_confidence):
        return text
    return None
