"""Distributed Redis rate limiter using fixed-window counter."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.providers.cache import get_redis

logger = logging.getLogger(__name__)

# Lua script for atomic INCR + EXPIRE (fixed-window)
_LUA_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end

if current > limit then
    local ttl = redis.call('TTL', key)
    return ttl
end

return -1
"""


async def check_rate_limit(client_ip: str) -> int | None:
    """Check the rate limit for *client_ip*.

    Returns ``None`` if the request is allowed, or the number of seconds
    until the window resets (``Retry-After``) if the limit is exceeded.
    """
    try:
        r = await get_redis()
        key = f"civicpulse:ratelimit:{client_ip}"
        result = await r.eval(
            _LUA_SCRIPT,
            1,
            key,
            str(settings.RATE_LIMIT_PER_MIN),
            "60",  # 60-second window
        )
        if result == -1:
            return None  # allowed
        return int(result)  # retry-after seconds
    except Exception as exc:
        logger.warning("Redis rate limiter unavailable (failing open): %s", exc)
        return None  # fail open so dev/outage does not block traffic
