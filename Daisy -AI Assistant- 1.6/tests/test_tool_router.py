"""Tests for the MCP tool router (0.9)."""
from services.tool_router import KeywordRouter, build_tool_router


def _tools():
    return [
        {"name": "take_screenshot", "description": "Capture the screen contents."},
        {"name": "open_application", "description": "Launch a Mac application by name."},
        {"name": "create_calendar_event", "description": "Add a meeting to the user's calendar."},
        {"name": "build_with_retry", "description": "Run the iOS / Xcode build and retry on common errors."},
        {"name": "send_email", "description": "Compose and send an email message."},
    ]


def test_keyword_router_ranks_relevant_tool_first():
    r = KeywordRouter()
    out = r.top_k("take a screenshot of Xcode", _tools(), k=3)
    assert out[0]["name"] in ("take_screenshot", "build_with_retry")


def test_keyword_router_returns_at_most_k():
    r = KeywordRouter()
    out = r.top_k("schedule meeting", _tools(), k=2)
    assert len(out) == 2


def test_factory_returns_a_router():
    r = build_tool_router(config=None)
    out = r.top_k("anything", _tools(), k=1)
    assert isinstance(out, list)
    assert len(out) == 1
