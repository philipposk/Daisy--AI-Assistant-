"""Long-term memory store for Daisy (1.3).

Two-layer system:
  1. MemoryStore — SQLite-backed fact store (key=topic, value=text snippet)
  2. ConversationSummarizer — compresses old turns into a single summary message

No pip deps. Keyword-based recall (no embeddings required).
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils import get_logger

logger = get_logger("memory")


# ---------------------------------------------------------------------------
# MemoryStore — stores arbitrary facts keyed by topic
# ---------------------------------------------------------------------------

class MemoryStore:
    """
    Persistent fact store backed by SQLite.

    Schema:
        memories(id, topic, content, source, created_at, updated_at, access_count)

    `topic` is a short keyword (e.g. "user_name", "preferred_language").
    `content` is the remembered text.
    `source` is how it was learned ("conversation", "explicit", etc.).
    """

    CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS memories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        topic       TEXT NOT NULL,
        content     TEXT NOT NULL,
        source      TEXT DEFAULT 'conversation',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL,
        access_count INTEGER DEFAULT 0
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_topic ON memories(topic);
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            for stmt in self.CREATE_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        conn.execute(stmt)
                    except sqlite3.OperationalError:
                        pass  # index may already exist

    # ------------------------------------------------------------------

    def remember(self, topic: str, content: str, source: str = "conversation") -> None:
        """Store or update a memory."""
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (topic, content, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(topic) DO UPDATE SET
                    content = excluded.content,
                    source  = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (topic, content, source, now, now),
            )
        logger.debug("Memory stored: %s", topic)

    def recall(self, topic: str) -> Optional[str]:
        """Retrieve a memory by exact topic."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET access_count = access_count + 1 WHERE topic = ?",
                (topic,),
            )
            row = conn.execute(
                "SELECT content FROM memories WHERE topic = ?", (topic,)
            ).fetchone()
        return row["content"] if row else None

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Keyword search across topic + content.
        Returns list of {"topic": ..., "content": ..., "score": ...} sorted by score desc.
        """
        words = [w.lower() for w in re.split(r'\W+', query) if len(w) > 2]
        if not words:
            return []

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT topic, content FROM memories ORDER BY updated_at DESC LIMIT 200"
            ).fetchall()

        scored = []
        for row in rows:
            combined = (row["topic"] + " " + row["content"]).lower()
            score = sum(1 for w in words if w in combined)
            if score > 0:
                scored.append({"topic": row["topic"], "content": row["content"], "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def forget(self, topic: str) -> bool:
        """Delete a memory. Returns True if it existed."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM memories WHERE topic = ?", (topic,))
        return cur.rowcount > 0

    def list_all(self, limit: int = 100) -> list[dict]:
        """Return all memories ordered by most recently updated."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT topic, content, source, updated_at FROM memories ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# ConversationSummarizer — compress old turns via simple extractive summary
# ---------------------------------------------------------------------------

class ConversationSummarizer:
    """
    Keeps conversation history from bloating.

    When the history exceeds `max_turns` messages, the oldest `compress_n`
    turns are replaced with a single "summary" system message.

    Summary strategy (no LLM required):
      - Extract the first sentence from each assistant message.
      - Extract the whole text of each user message (capped at 80 chars).
      - Join as bullet list under "Earlier conversation summary:".

    If a `brain_service` is provided, it tries to use the LLM to produce a
    better summary (one paragraph), falling back to the extractive approach
    on failure.
    """

    def __init__(
        self,
        max_turns: int = 20,
        compress_n: int = 10,
        brain_service=None,
    ):
        self.max_turns = max_turns
        self.compress_n = compress_n
        self.brain = brain_service

    # ------------------------------------------------------------------

    def maybe_compress(self, messages: list[dict]) -> list[dict]:
        """
        Given a list of message dicts ({"role": ..., "content": ...}),
        return a (possibly shorter) list where old turns have been summarized.
        """
        if len(messages) <= self.max_turns:
            return messages

        to_compress = messages[: self.compress_n]
        keep = messages[self.compress_n :]

        summary_text = self._summarize(to_compress)
        summary_msg = {
            "role": "system",
            "content": f"[Earlier conversation summary]\n{summary_text}",
        }
        logger.info(
            "Compressed %d messages → 1 summary (%d remain)",
            len(to_compress),
            len(keep),
        )
        return [summary_msg] + keep

    def _summarize(self, messages: list[dict]) -> str:
        """Try LLM summary; fall back to extractive."""
        if self.brain is not None:
            try:
                return self._llm_summary(messages)
            except Exception as exc:
                logger.warning("LLM summary failed: %s; using extractive", exc)
        return self._extractive_summary(messages)

    def _extractive_summary(self, messages: list[dict]) -> str:
        lines = []
        for m in messages:
            role = m.get("role", "unknown")
            content = str(m.get("content", ""))
            if role == "user":
                snippet = content[:80].replace("\n", " ")
                lines.append(f"User: {snippet}")
            elif role == "assistant":
                # first sentence
                first = re.split(r'(?<=[.!?])\s', content)[0][:120]
                lines.append(f"Assistant: {first}")
        return "\n".join(lines) if lines else "(empty)"

    def _llm_summary(self, messages: list[dict]) -> str:
        """Ask the brain service to produce a one-paragraph summary."""
        transcript = "\n".join(
            f"{m.get('role','?').upper()}: {m.get('content','')[:200]}"
            for m in messages
        )
        prompt = (
            "Summarize the following conversation excerpt in 2-3 sentences. "
            "Preserve key facts (names, decisions, action items).\n\n"
            + transcript
        )
        # Use brain service's raw LLM call if available
        if hasattr(self.brain, "_call_openai"):
            result = self.brain._call_openai(prompt)
        elif hasattr(self.brain, "_call_anthropic"):
            result = self.brain._call_anthropic(prompt)
        else:
            raise RuntimeError("No suitable LLM call method")
        return str(result)[:500]
