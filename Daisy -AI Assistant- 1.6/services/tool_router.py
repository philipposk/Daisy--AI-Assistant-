"""
Embedding-based MCP tool router (0.9).

Once you have many MCP servers wired in, dumping every tool description into
the system prompt costs tokens and confuses the LLM. The router scores tools
against the user's transcript and only the top-K relevant ones are surfaced.

Two backends:
- EmbeddingRouter: uses `sentence-transformers` if installed. Local, free.
- KeywordRouter: cheap fallback — Jaccard / token-overlap. Always works.

Public API:
    router = build_tool_router(config)
    selected = router.top_k(transcript, all_tools, k=8)
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from utils import get_logger

logger = get_logger("tool_router")


class _Base:
    def top_k(self, query: str, tools: List[Dict[str, Any]], k: int = 8) -> List[Dict[str, Any]]:
        raise NotImplementedError


class KeywordRouter(_Base):
    """Cheap fallback. Tokenises both sides and ranks by overlap."""

    _SPLIT = re.compile(r"[^a-zA-Z0-9]+")

    def _tokens(self, text: str) -> set:
        return {t.lower() for t in self._SPLIT.split(text or "") if len(t) > 2}

    def top_k(self, query: str, tools: List[Dict[str, Any]], k: int = 8) -> List[Dict[str, Any]]:
        q = self._tokens(query)
        scored = []
        for tool in tools:
            descr = (tool.get("description") or "") + " " + (tool.get("name") or "")
            t = self._tokens(descr)
            overlap = len(q & t)
            scored.append((overlap, tool))
        scored.sort(key=lambda p: p[0], reverse=True)
        return [tool for score, tool in scored[:k]]


class EmbeddingRouter(_Base):
    """sentence-transformers-backed. Cached encodings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers not installed. Falling back to keyword router."
            ) from e
        self._model = SentenceTransformer(model_name)
        self._cache: Dict[str, Any] = {}

    def _embed(self, text: str):
        if text in self._cache:
            return self._cache[text]
        vec = self._model.encode(text, normalize_embeddings=True)
        self._cache[text] = vec
        return vec

    def top_k(self, query: str, tools: List[Dict[str, Any]], k: int = 8) -> List[Dict[str, Any]]:
        import numpy as np  # pulled in by sentence-transformers
        q = self._embed(query)
        scores = []
        for tool in tools:
            text = (tool.get("name") or "") + " — " + (tool.get("description") or "")
            v = self._embed(text)
            scores.append((float(np.dot(q, v)), tool))
        scores.sort(key=lambda p: p[0], reverse=True)
        return [tool for s, tool in scores[:k]]


def build_tool_router(config=None) -> _Base:
    """Pick the best router available."""
    try:
        return EmbeddingRouter()
    except Exception as e:
        logger.info(f"EmbeddingRouter unavailable ({e}); using KeywordRouter.")
        return KeywordRouter()
