"""Provider observability endpoint.

GET /api/meta/providers — which triage provider is active and last 20 outcomes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.database import DatabaseSession, get_db
from app.providers.cache import get_triage_cache_metrics
from app.services.complaint_service import (
    get_active_provider_name,
    get_recent_outcomes_with_db,
)

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers")
async def provider_info(db: DatabaseSession = Depends(get_db)):
    """Which triage provider is active, last 20 triage outcomes, and cache hit metrics."""
    outcomes = await get_recent_outcomes_with_db(db, limit=20)
    cache_metrics = await get_triage_cache_metrics()

    return {
        "active_provider": get_active_provider_name(),
        "recent_outcomes": outcomes,
        "triage_cache": cache_metrics,
    }
