"""Complaint service — triage orchestration, state machine, business rules.

No SQL here; all persistence goes through the repository.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from collections import deque

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import TRANSITIONS, Status
from app.providers.cache import (
    get_cached_triage,
    invalidate_stats_cache,
    set_cached_triage,
)
from app.providers.triage.factory import get_triage_provider
from app.providers.triage.rules import RuleBasedTriage
from app.repositories import complaint_repository
from app.schemas.complaint import ComplaintCreate
from app.schemas.triage import TriageResult

logger = logging.getLogger(__name__)

# ── In-memory record of recent triage outcomes (last 20) ────────────
_triage_outcomes: deque[dict] = deque(maxlen=20)

# ── Lazy-initialised provider ────────────────────────────────────────
_provider = None


def _get_provider():
    global _provider
    if _provider is None:
        _provider = get_triage_provider()
    return _provider


class InvalidTransition(Exception):
    """Raised when a status transition is not allowed."""

    def __init__(self, from_status: Status, to_status: Status) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Invalid transition from {from_status.value} to {to_status.value}")


def validate_transition(current: Status, target: Status) -> Status:
    """Validate a status transition against the explicit transition table."""
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(current, target)
    return target


async def _run_triage(text: str, location: str) -> tuple[TriageResult, str, int]:
    """Run triage with timeout, single jittered retry, and fallback.

    Returns (result, triaged_by, latency_ms).
    """
    provider = _get_provider()

    # Check triage cache first
    cached = await get_cached_triage(text, location)
    if cached is not None:
        result = TriageResult.model_validate(cached)
        return result, f"{provider.name}:cached", 0

    start = time.monotonic()
    provider_name = getattr(provider, "name", "unknown")

    # Attempt with the primary provider (with retry on retryable errors)
    for attempt in range(2):  # 1 original + 1 retry
        try:
            result = await asyncio.wait_for(
                provider.triage(text, location),
                timeout=10.0,
            )
            latency_ms = int((time.monotonic() - start) * 1000)

            # Cache the successful result
            await set_cached_triage(text, location, result.model_dump(mode="json"))

            _triage_outcomes.append(
                {
                    "provider": provider_name,
                    "latency_ms": latency_ms,
                    "fallback": False,
                }
            )

            return result, provider_name, latency_ms

        except (TimeoutError, Exception) as exc:
            if attempt == 0:
                # Retry with jitter on retryable errors
                jitter = random.uniform(0.5, 1.5)
                logger.warning(
                    "triage_retry: provider=%s error_class=%s attempt=%d jitter=%.2f",
                    provider_name,
                    type(exc).__name__,
                    attempt + 1,
                    jitter,
                )
                await asyncio.sleep(jitter)
            else:
                logger.warning(
                    "triage_fallback: provider=%s error_class=%s error=%s",
                    provider_name,
                    type(exc).__name__,
                    str(exc)[:200],
                )

    # Fallback to RuleBasedTriage — a user must never see a 500
    fallback = RuleBasedTriage()
    result = await fallback.triage(text, location)
    latency_ms = int((time.monotonic() - start) * 1000)

    _triage_outcomes.append(
        {
            "provider": "rules:fallback",
            "latency_ms": latency_ms,
            "fallback": True,
        }
    )

    return result, "rules:fallback", latency_ms


async def create_complaint(
    db: AsyncSession,
    payload: ComplaintCreate,
) -> complaint_repository.Complaint:
    """Validate → triage → persist. Invalidate stats cache on write."""
    result, triaged_by, latency_ms = await _run_triage(payload.text, payload.location)

    complaint = await complaint_repository.create_complaint(
        db,
        complaint_text=payload.text,
        location=payload.location,
        reporter_contact=payload.reporter_contact,
        category=result.category,
        priority=result.priority,
        ai_summary=result.summary,
        triaged_by=triaged_by,
        triage_latency_ms=latency_ms,
    )

    # Invalidate stats cache so new complaint appears immediately
    await invalidate_stats_cache()

    return complaint


async def get_complaint(db: AsyncSession, complaint_id: uuid.UUID):
    """Fetch a single complaint by ID."""
    return await complaint_repository.get_complaint_by_id(db, complaint_id)


async def list_complaints(
    db: AsyncSession,
    *,
    category=None,
    priority=None,
    status=None,
    page: int = 1,
    page_size: int = 20,
):
    """List complaints with pagination and filters."""
    return await complaint_repository.list_complaints(
        db,
        category=category,
        priority=priority,
        status=status,
        page=page,
        page_size=page_size,
    )


async def update_status(
    db: AsyncSession,
    complaint_id: uuid.UUID,
    target_status: Status,
):
    """Validate transition and update status."""
    complaint = await complaint_repository.get_complaint_by_id(db, complaint_id)
    if complaint is None:
        return None

    # Validate against the explicit transition table
    validate_transition(complaint.status, target_status)

    updated = await complaint_repository.update_complaint_status(db, complaint_id, target_status)

    # Invalidate stats cache on status change
    await invalidate_stats_cache()

    return updated


def get_active_provider_name() -> str:
    """Return the name of the currently active triage provider."""
    return _get_provider().name


def get_recent_outcomes() -> list[dict]:
    """Return the last 20 triage outcomes."""
    return list(_triage_outcomes)
