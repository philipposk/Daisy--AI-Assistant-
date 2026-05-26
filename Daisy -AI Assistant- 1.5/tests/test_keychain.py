"""Tests for the Keychain helper (1.1).

We don't actually hit the real keychain in CI — we monkeypatch subprocess.run.
"""
import subprocess
from unittest.mock import patch, MagicMock

from services import keychain


def test_known_keys_present():
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "GOOGLE_API_KEY"):
        assert k in keychain.KNOWN_KEYS


def test_get_secret_returns_value():
    fake = MagicMock(returncode=0, stdout="sk-xyz\n", stderr="")
    with patch.object(keychain, "keychain_available", return_value=True), \
         patch("services.keychain.subprocess.run", return_value=fake):
        assert keychain.get_secret("OPENAI_API_KEY") == "sk-xyz"


def test_get_secret_returns_none_on_failure():
    fake = MagicMock(returncode=44, stdout="", stderr="not found")
    with patch.object(keychain, "keychain_available", return_value=True), \
         patch("services.keychain.subprocess.run", return_value=fake):
        assert keychain.get_secret("OPENAI_API_KEY") is None


def test_get_secret_none_when_unavailable():
    with patch.object(keychain, "keychain_available", return_value=False):
        assert keychain.get_secret("OPENAI_API_KEY") is None


def test_set_secret_returns_true():
    fake = MagicMock(returncode=0, stdout="", stderr="")
    with patch.object(keychain, "keychain_available", return_value=True), \
         patch("services.keychain.subprocess.run", return_value=fake):
        assert keychain.set_secret("OPENAI_API_KEY", "sk-xyz") is True


def test_set_secret_rejects_empty():
    with patch.object(keychain, "keychain_available", return_value=True):
        assert keychain.set_secret("OPENAI_API_KEY", "") is False


def test_delete_secret():
    fake = MagicMock(returncode=0, stdout="", stderr="")
    with patch.object(keychain, "keychain_available", return_value=True), \
         patch("services.keychain.subprocess.run", return_value=fake):
        assert keychain.delete_secret("OPENAI_API_KEY") is True


def test_list_known_filters_unset():
    def fake_get(name):
        return "sk-only-openai" if name == "OPENAI_API_KEY" else None
    with patch.object(keychain, "get_secret", side_effect=fake_get):
        out = keychain.list_known()
        assert out == ["OPENAI_API_KEY"]
