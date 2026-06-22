"""Tests for the macOS permissions module (1.0)."""
from services.permissions import (
    check_permissions, open_settings, summary_line, _PANE,
)


def test_check_permissions_shape():
    r = check_permissions()
    assert set(r) == {"microphone", "accessibility", "screen_recording"}
    for v in r.values():
        assert isinstance(v, bool)


def test_summary_line_all_granted():
    assert "All permissions granted." == summary_line(
        {"microphone": True, "accessibility": True, "screen_recording": True}
    )


def test_summary_line_lists_missing():
    out = summary_line({"microphone": False, "accessibility": True, "screen_recording": False})
    assert "microphone" in out and "screen_recording" in out


def test_open_settings_unknown_kind_returns_false():
    # Even on macOS, unknown kind is a no-op false.
    assert open_settings("bogus") is False


def test_pane_map_has_known_kinds():
    for k in ("mic", "accessibility", "screen"):
        assert k in _PANE
        assert _PANE[k].startswith("x-apple.systempreferences:")
