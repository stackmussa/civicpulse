"""Health and readiness probes.

GET /health — liveness. MUST NOT touch the database.
GET /ready  — readiness. 200 only if Postgres and Redis are both reachable.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.core.database import check_database_health
from app.providers.cache import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness probe — process is alive, no dependency check."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe — 200 only if Postgres AND Redis are reachable."""
    # Check Postgres
    try:
        await check_database_health()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": "not_ready", "failed": "postgres"},
        )

    # Check Redis
    try:
        r = await get_redis()
        await r.ping()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"error": "not_ready", "failed": "redis"},
        )

    return {"status": "ok"}
