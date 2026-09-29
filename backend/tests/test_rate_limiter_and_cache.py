"""Tests for rate limiting logic and cache hashing."""

import pytest

from app.providers.cache import _triage_cache_key


def test_triage_cache_key_deterministic():
    """Triage cache key produces stable SHA256 hashes for identical inputs."""
    k1 = _triage_cache_key("water leaking", "sector 1")
    k2 = _triage_cache_key("water leaking", "sector 1")
    k3 = _triage_cache_key("water leaking", "sector 2")

    assert k1 == k2
    assert k1.startswith("civicpulse:triage:")
    assert k1 != k3


@pytest.mark.asyncio
async def test_rate_limiter_exceeded_returns_429(client, monkeypatch):
    """When check_rate_limit indicates limit is reached, POST returns 429 with Retry-After."""

    # Mock check_rate_limit to return retry-after 45 seconds
    async def mock_rate_limit(ip: str):
        return 45

    from app.routes import complaints as complaints_route

    monkeypatch.setattr(complaints_route, "check_rate_limit", mock_rate_limit)

    response = await client.post(
        "/api/complaints",
        json={
            "text": "Water pipeline leak on main expressway",
            "location": "Expressway, Islamabad",
        },
    )
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "45"
    data = response.json()
    assert data["error"] == "rate_limit_exceeded"
    assert data["retry_after"] == 45
