"""Deterministic fake for CI — seeded, no network, configurable failure injection."""

from __future__ import annotations

import hashlib

from app.models.complaint import Category, Priority
from app.schemas.triage import TriageResult

# Fixed rotation for deterministic output based on content hash
_CATEGORIES = list(Category)
_PRIORITIES = list(Priority)


class SimulatedTriage:
    """Deterministic provider for CI.

    Uses a content hash to produce repeatable results.
    Set ``fail=True`` to inject failures for fallback testing.
    """

    name: str = "simulated"

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def triage(self, text: str, location: str) -> TriageResult:
        if self._fail:
            raise RuntimeError("SimulatedTriage: injected failure for testing")

        # Deterministic hash → stable category and priority
        digest = hashlib.sha256(f"{text}{location}".encode()).hexdigest()
        cat_idx = int(digest[:8], 16) % len(_CATEGORIES)
        pri_idx = int(digest[8:16], 16) % len(_PRIORITIES)

        return TriageResult(
            category=_CATEGORIES[cat_idx],
            priority=_PRIORITIES[pri_idx],
            summary=f"[simulated] {text[:80]}".strip()[:140],
            confidence=0.85,
        )
