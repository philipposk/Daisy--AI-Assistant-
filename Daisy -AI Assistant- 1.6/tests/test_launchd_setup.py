"""Tests for tools/launchd_setup.py (1.5)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.launchd_setup import generate_plist, LABEL, DEFAULT_PORT


def test_generate_plist_contains_label():
    plist = generate_plist()
    assert LABEL in plist


def test_generate_plist_contains_port():
    plist = generate_plist(port=9999)
    assert "9999" in plist


def test_generate_plist_contains_daisy_app():
    plist = generate_plist()
    assert "daisy_app.py" in plist


def test_generate_plist_contains_no_ui():
    plist = generate_plist()
    assert "--no-ui" in plist


def test_generate_plist_is_valid_xml_structure():
    plist = generate_plist()
    assert plist.strip().startswith("<?xml")
    assert "<plist" in plist
    assert "</plist>" in plist


def test_generate_plist_has_keepalive():
    plist = generate_plist()
    assert "KeepAlive" in plist
    assert "<true/>" in plist


def test_generate_plist_default_port():
    plist = generate_plist()
    assert str(DEFAULT_PORT) in plist
