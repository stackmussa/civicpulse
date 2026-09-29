"""Provider observability endpoint.

GET /api/meta/providers — which triage provider is active and last 20 outcomes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories import complaint_repository
from app.services.complaint_service import get_active_provider_name, get_recent_outcomes

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/providers")
async def provider_info(db: AsyncSession = Depends(get_db)):
    """Which triage provider is active and the last 20 triage outcomes."""
    # Merge in-memory recent outcomes with DB outcomes
    in_memory = get_recent_outcomes()
    if len(in_memory) < 20:
        db_outcomes = await complaint_repository.get_recent_triage_outcomes(
            db, limit=20 - len(in_memory)
        )
        outcomes = in_memory + db_outcomes
    else:
        outcomes = in_memory

    return {
        "active_provider": get_active_provider_name(),
        "recent_outcomes": outcomes[:20],
    }
