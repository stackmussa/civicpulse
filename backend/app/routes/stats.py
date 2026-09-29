"""Stats endpoint with read-through Redis cache.

GET /api/stats — aggregates, cached 30 s, X-Cache: HIT|MISS header.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.core.database import DatabaseSession, get_db
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(db: DatabaseSession = Depends(get_db)):
    """Aggregate counts by category and priority, Redis-cached, TTL 30 s."""
    data, cache_hit = await stats_service.get_stats(db)

    return JSONResponse(
        content=data,
        headers={"X-Cache": "HIT" if cache_hit else "MISS"},
    )
