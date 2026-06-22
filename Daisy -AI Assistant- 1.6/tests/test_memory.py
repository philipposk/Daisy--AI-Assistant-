"""Tests for services/memory.py (1.3)."""
import tempfile
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.memory import MemoryStore, ConversationSummarizer


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------

def _store(tmp_dir=None):
    if tmp_dir is None:
        tmp_dir = tempfile.mkdtemp()
    return MemoryStore(Path(tmp_dir) / "mem.db")


def test_remember_and_recall():
    s = _store()
    s.remember("user_name", "Alice")
    assert s.recall("user_name") == "Alice"


def test_recall_missing_returns_none():
    s = _store()
    assert s.recall("nonexistent_topic") is None


def test_remember_overwrites():
    s = _store()
    s.remember("color", "blue")
    s.remember("color", "red")
    assert s.recall("color") == "red"


def test_forget_returns_true():
    s = _store()
    s.remember("lang", "Python")
    assert s.forget("lang") is True


def test_forget_missing_returns_false():
    s = _store()
    assert s.forget("no_such_topic") is False


def test_search_finds_match():
    s = _store()
    s.remember("preferred_language", "I prefer Python for scripting")
    s.remember("hobby", "I enjoy cycling")
    results = s.search("python scripting")
    assert len(results) > 0
    assert results[0]["topic"] == "preferred_language"


def test_search_empty_query_returns_empty():
    s = _store()
    s.remember("x", "something")
    assert s.search("") == []


def test_search_no_match_returns_empty():
    s = _store()
    s.remember("color", "blue")
    assert s.search("xyz unknown") == []


def test_list_all_returns_memories():
    s = _store()
    s.remember("a", "alpha")
    s.remember("b", "beta")
    all_mem = s.list_all()
    topics = [m["topic"] for m in all_mem]
    assert "a" in topics
    assert "b" in topics


def test_search_respects_limit():
    s = _store()
    for i in range(10):
        s.remember(f"topic_{i}", f"value about testing item {i}")
    results = s.search("testing", limit=3)
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# ConversationSummarizer
# ---------------------------------------------------------------------------

def _make_messages(n):
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append({"role": role, "content": f"Message {i}: some content here"})
    return msgs


def test_no_compression_when_below_threshold():
    s = ConversationSummarizer(max_turns=20, compress_n=10)
    msgs = _make_messages(10)
    result = s.maybe_compress(msgs)
    assert result == msgs  # unchanged


def test_compression_triggers_when_exceeded():
    s = ConversationSummarizer(max_turns=5, compress_n=3)
    msgs = _make_messages(8)
    result = s.maybe_compress(msgs)
    # Should have fewer messages (3 compressed to 1 summary + remaining 5)
    assert len(result) < len(msgs)
    # First message should be the summary
    assert result[0]["role"] == "system"
    assert "summary" in result[0]["content"].lower() or "earlier" in result[0]["content"].lower()


def test_compressed_keeps_remaining_intact():
    s = ConversationSummarizer(max_turns=5, compress_n=3)
    msgs = _make_messages(8)
    result = s.maybe_compress(msgs)
    # The keep portion (msgs[3:]) should appear in result (after summary)
    original_keep = msgs[3:]
    result_keep = result[1:]
    assert result_keep == original_keep


def test_extractive_summary_includes_content():
    s = ConversationSummarizer(max_turns=3, compress_n=2)
    msgs = [
        {"role": "user", "content": "Tell me about cats"},
        {"role": "assistant", "content": "Cats are small mammals. They make great pets."},
    ]
    # Trigger compression (exceeds max_turns=1 ... use lower threshold)
    s2 = ConversationSummarizer(max_turns=1, compress_n=2)
    result = s2.maybe_compress(msgs + [{"role": "user", "content": "New question"}])
    assert result[0]["role"] == "system"
    summary = result[0]["content"]
    assert "cats" in summary.lower() or "Tell me" in summary
