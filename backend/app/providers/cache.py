"""Redis cache provider for stats and triage result caching."""

from __future__ import annotations

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

STATS_CACHE_KEY = "civicpulse:stats"


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the async Redis connection."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── Stats cache (Job 1) ─────────────────────────────────────────────


async def get_cached_stats() -> tuple[dict | None, bool]:
    """Return (data, is_hit). data is None on miss."""
    try:
        r = await get_redis()
        raw = await r.get(STATS_CACHE_KEY)
        if raw is not None:
            return json.loads(raw), True
    except Exception as exc:
        logger.warning("Redis get_cached_stats error: %s", exc)
    return None, False


async def set_cached_stats(data: dict) -> None:
    """Store stats in Redis with the configured TTL."""
    try:
        r = await get_redis()
        await r.set(STATS_CACHE_KEY, json.dumps(data), ex=settings.STATS_CACHE_TTL)
    except Exception as exc:
        logger.warning("Redis set_cached_stats error: %s", exc)


async def invalidate_stats_cache() -> None:
    """Delete the stats cache — called on every write."""
    try:
        r = await get_redis()
        await r.delete(STATS_CACHE_KEY)
    except Exception as exc:
        logger.warning("Redis invalidate_stats_cache error: %s", exc)


# ── Triage result cache (Job: content-hash caching) ─────────────────


def _triage_cache_key(text: str, location: str) -> str:
    digest = hashlib.sha256(f"{text}|{location}".encode()).hexdigest()
    return f"civicpulse:triage:{digest}"


async def get_cached_triage(text: str, location: str) -> dict | None:
    """Return cached triage result or None."""
    try:
        r = await get_redis()
        raw = await r.get(_triage_cache_key(text, location))
        if raw is not None:
            logger.debug("Triage cache HIT")
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis get_cached_triage error: %s", exc)
    return None


async def set_cached_triage(text: str, location: str, data: dict) -> None:
    """Cache a triage result by content hash with 24 h TTL."""
    try:
        r = await get_redis()
        await r.set(
            _triage_cache_key(text, location),
            json.dumps(data),
            ex=settings.TRIAGE_CACHE_TTL,
        )
    except Exception as exc:
        logger.warning("Redis set_cached_triage error: %s", exc)
