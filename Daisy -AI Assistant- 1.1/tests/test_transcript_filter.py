"""Tests for the Whisper hallucination filter (0.9)."""
from services.transcript_filter import is_probably_real, filter_transcript


def test_real_text_passes():
    assert is_probably_real("Create a note about pasta") is True


def test_empty_drops():
    assert is_probably_real("") is False
    assert is_probably_real("   ") is False
    assert is_probably_real(None) is False


def test_phantoms_drop():
    assert is_probably_real("thanks for watching") is False
    assert is_probably_real("Thanks for watching!") is False
    assert is_probably_real("Subscribe to my channel") is False
    assert is_probably_real("[music]") is False


def test_bare_punctuation_drops():
    assert is_probably_real(".") is False
    assert is_probably_real("...") is False


def test_filter_transcript_returns_none_for_phantom():
    assert filter_transcript("thanks for watching") is None
    assert filter_transcript("real sentence here") == "real sentence here"


def test_low_confidence_drops():
    assert is_probably_real("yes", confidence=0.1, min_confidence=0.5) is False
    assert is_probably_real("yes", confidence=0.9, min_confidence=0.5) is True
