"""Deterministic fake for CI — seeded, no network, configurable failure injection."""

from __future__ import annotations

from app.models.complaint import Category, Priority
from app.schemas.triage import TriageResult

# Deterministic content-based classification rules
CATEGORY_RULES: tuple[tuple[Category, tuple[str, ...]], ...] = (
    (
        Category.water,
        (
            "water",
            "pipe",
            "pipeline",
            "leak",
            "leaking",
            "flooding",
            "flood",
            "sewer",
            "pani",
            "paani",
        ),
    ),
    (
        Category.streetlights,
        (
            "streetlight",
            "street light",
            "streetlights",
            "lamp",
            "bulb",
            "dark at night",
            "dark street",
        ),
    ),
    (
        Category.electricity,
        (
            "electric",
            "electricity",
            "transformer",
            "power",
            "wire",
            "outage",
            "spark",
            "bijli",
        ),
    ),
    (
        Category.sanitation,
        ("garbage", "kachra", "trash", "waste", "dump", "sewage", "drain"),
    ),
    (
        Category.roads,
        ("road", "pothole", "potholes", "traffic", "highway", "asphalt"),
    ),
)

PRIORITY_RULES: tuple[tuple[Priority, tuple[str, ...]], ...] = (
    (
        Priority.high,
        (
            "urgent",
            "danger",
            "burst",
            "flood",
            "flooding",
            "spark",
            "fire",
            "emergency",
            "fatal",
            "immediately",
            "hazard",
        ),
    ),
    (
        Priority.low,
        ("minor", "cosmetic", "slow", "delay"),
    ),
)


def classify_category(text: str) -> Category:
    """Classify complaint text into a Category deterministically by keyword."""
    normalized = text.casefold()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in normalized for keyword in keywords):
            return category
    return Category.other


def infer_priority(text: str) -> Priority:
    """Infer complaint priority deterministically by urgency keywords."""
    normalized = text.casefold()
    for priority, keywords in PRIORITY_RULES:
        if any(keyword in normalized for keyword in keywords):
            return priority
    return Priority.normal


class SimulatedTriage:
    """Deterministic provider for CI.

    Uses complaint content classification to produce repeatable results.
    Set ``fail=True`` to inject failures for fallback testing.
    """

    name: str = "simulated"

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def triage(self, text: str, location: str) -> TriageResult:
        if self._fail:
            raise RuntimeError("SimulatedTriage: injected failure for testing")

        category = classify_category(text)
        priority = infer_priority(text)

        return TriageResult(
            category=category,
            priority=priority,
            summary=f"[simulated] {text[:80]}".strip()[:140],
            confidence=0.85,
        )
