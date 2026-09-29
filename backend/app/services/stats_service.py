"""Stats service — read-through cache orchestration for /api/stats."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.cache import get_cached_stats, set_cached_stats
from app.repositories import complaint_repository


async def get_stats(db: AsyncSession) -> tuple[dict, bool]:
    """Return (stats_dict, cache_hit).

    Implements the read-through cache pattern:
    1. Try Redis cache first.
    2. On miss, query the DB and populate the cache.
    """
    cached, is_hit = await get_cached_stats()
    if cached is not None:
        return cached, True

    # Cache miss — compute from the database
    stats = await complaint_repository.get_stats(db)

    # Store in cache for next request
    await set_cached_stats(stats)

    return stats, False
