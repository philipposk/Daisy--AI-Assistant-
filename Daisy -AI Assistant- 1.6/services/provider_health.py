"""Provider health: circuit breakers + cost tracking (1.6).

Idea ported from the author's AI-OS project. Two concerns:

1. **Circuit breaker** — if a provider fails N times in a row (bad key, outage,
   rate limit), stop trying it for a cooldown window instead of burning a
   slow timeout on every single turn. After the cooldown it gets one trial
   request ("half-open"); success closes the breaker, failure re-opens it.

2. **Cost tracking** — a rough running estimate of what each provider has
   cost, so a forgotten Anthropic key can't quietly rack up spend. Estimates
   only (we don't see real token counts here), persisted to
   `~/.daisy/costs.json`.

Both are process-wide singletons guarded by a lock; safe under the threadpool
that serves the HTTP API.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from utils import get_logger

logger = get_logger("provider_health")

# Failures-in-a-row before a provider's breaker opens.
FAILURE_THRESHOLD = 3
# How long (seconds) a breaker stays open before allowing a trial request.
COOLDOWN_SECONDS = 120.0

# Very rough $/1K-token estimates (blended input+output) per provider, used
# only for the running spend gauge. local_http / free are $0.
_COST_PER_1K = {
    "openai": 0.005,
    "anthropic": 0.006,
    "groq": 0.0,        # free tier
    "free": 0.0,
    "local_http": 0.0,
}
# Tokens are not exposed here; assume a typical turn ~ this many.
_ASSUMED_TOKENS_PER_CALL = 800


@dataclass
class _BreakerState:
    failures: int = 0
    opened_at: Optional[float] = None  # monotonic time the breaker opened


class CircuitBreaker:
    """Per-provider failure tracking with a cooldown window."""

    def __init__(self, threshold: int = FAILURE_THRESHOLD, cooldown: float = COOLDOWN_SECONDS):
        self._threshold = threshold
        self._cooldown = cooldown
        self._state: Dict[str, _BreakerState] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.monotonic()

    def allow(self, provider: str) -> bool:
        """True if a request to `provider` should be attempted."""
        with self._lock:
            st = self._state.get(provider)
            if st is None or st.opened_at is None:
                return True
            # Breaker open — allow a single trial once the cooldown elapsed.
            if self._now() - st.opened_at >= self._cooldown:
                return True
            return False

    def record_success(self, provider: str) -> None:
        with self._lock:
            self._state[provider] = _BreakerState()

    def record_failure(self, provider: str) -> None:
        with self._lock:
            st = self._state.setdefault(provider, _BreakerState())
            st.failures += 1
            if st.failures >= self._threshold and st.opened_at is None:
                st.opened_at = self._now()
                logger.warning(
                    "Circuit breaker OPEN for provider '%s' after %d failures",
                    provider, st.failures,
                )
            elif st.opened_at is not None:
                # Trial request during half-open failed → restart cooldown.
                st.opened_at = self._now()

    def status(self) -> Dict[str, dict]:
        with self._lock:
            out = {}
            for name, st in self._state.items():
                is_open = st.opened_at is not None and (self._now() - st.opened_at) < self._cooldown
                out[name] = {"failures": st.failures, "open": is_open}
            return out


class CostTracker:
    """Running estimated spend per provider, persisted to JSON."""

    def __init__(self, persist_path: Optional[Path] = None):
        self._persist_path = Path(persist_path).expanduser() if persist_path else None
        self._totals: Dict[str, float] = {}
        self._calls: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._load()

    def record_call(self, provider: str, tokens: int = _ASSUMED_TOKENS_PER_CALL) -> None:
        rate = _COST_PER_1K.get(provider, 0.0)
        cost = rate * (tokens / 1000.0)
        with self._lock:
            self._totals[provider] = self._totals.get(provider, 0.0) + cost
            self._calls[provider] = self._calls.get(provider, 0) + 1
            self._save()

    def summary(self) -> dict:
        with self._lock:
            return {
                "providers": {
                    name: {"calls": self._calls.get(name, 0),
                           "estimated_usd": round(total, 4)}
                    for name, total in self._totals.items()
                },
                "total_estimated_usd": round(sum(self._totals.values()), 4),
                "note": "Rough estimate — real token counts are not available client-side.",
            }

    def _load(self) -> None:
        if not self._persist_path or not self._persist_path.exists():
            return
        try:
            data = json.loads(self._persist_path.read_text() or "{}")
            self._totals = {k: float(v) for k, v in data.get("totals", {}).items()}
            self._calls = {k: int(v) for k, v in data.get("calls", {}).items()}
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.warning("Could not load cost data: %s", exc)

    def _save(self) -> None:
        """Atomic write; caller holds self._lock."""
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                dir=str(self._persist_path.parent), prefix=".costs-", suffix=".tmp"
            )
            with os.fdopen(fd, "w") as f:
                json.dump({"totals": self._totals, "calls": self._calls}, f, indent=2)
            os.replace(tmp, self._persist_path)
        except OSError as exc:
            logger.warning("Could not persist cost data: %s", exc)
