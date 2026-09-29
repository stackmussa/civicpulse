"""Deterministic keyword-based triage — the always-available fallback."""

from __future__ import annotations

from app.models.complaint import Category, Priority
from app.schemas.triage import TriageResult

# ── Keyword → category mapping ──────────────────────────────────────
_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.water: [
        "water", "pani", "paani", "flood", "pipe", "burst", "leak",
        "sewage", "nala", "drain", "supply", "tanker", "boring",
        "tap", "borehole", "overflow", "gutter",
    ],
    Category.electricity: [
        "electric", "bijli", "transformer", "wire", "power",
        "outage", "voltage", "load", "shedding", "spark", "pole",
        "cable", "current", "meter", "generator", "light",
    ],
    Category.sanitation: [
        "garbage", "kachra", "waste", "trash", "dump", "clean",
        "sweeper", "safai", "smell", "stink", "dustbin", "rubbish",
        "litter", "hygiene", "dirty", "filth",
    ],
    Category.roads: [
        "road", "pothole", "crack", "tar", "asphalt", "highway",
        "street", "footpath", "sidewalk", "pavement", "bridge",
        "gaddha", "construction", "barrier",
    ],
    Category.streetlights: [
        "streetlight", "light", "lamp", "bulb", "dark", "pole",
        "night", "broken light", "andhera",
    ],
}

# ── Priority keywords ────────────────────────────────────────────────
_HIGH_PRIORITY_KEYWORDS: list[str] = [
    "urgent", "emergency", "flood", "fire", "danger", "dangerous",
    "injury", "injured", "collapse", "collapsed", "burst",
    "electrocution", "spark", "short circuit", "foran", "jaldi",
    "immediately", "critical", "severe", "fatal",
]


class RuleBasedTriage:
    """Deterministic keyword matching — always available, never fails."""

    name: str = "rules"

    async def triage(self, text: str, location: str) -> TriageResult:
        combined = f"{text} {location}".lower()

        # Determine category
        best_category = Category.other
        best_score = 0
        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_category = category

        # Determine priority
        priority = Priority.normal
        high_hits = sum(1 for kw in _HIGH_PRIORITY_KEYWORDS if kw in combined)
        if high_hits >= 2:
            priority = Priority.high
        elif high_hits == 0 and best_score <= 1:
            priority = Priority.low

        # Build summary (truncated to 140 chars)
        summary = f"{best_category.value} issue reported at {location}"
        if priority == Priority.high:
            summary = f"URGENT: {summary}"
        summary = summary[:140]

        confidence = min(1.0, best_score * 0.2) if best_score > 0 else 0.1

        return TriageResult(
            category=best_category,
            priority=priority,
            summary=summary,
            confidence=confidence,
        )
