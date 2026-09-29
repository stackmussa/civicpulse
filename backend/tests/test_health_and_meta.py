"""Tests for health, readiness, meta providers, and metrics endpoints."""

import pytest


@pytest.mark.asyncio
async def test_health_check_does_not_touch_db(client):
    """GET /health is a liveness probe and returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_meta_providers_endpoint(client):
    """GET /api/meta/providers exposes the active provider and recent outcomes."""
    # Trigger a complaint to populate recent outcomes
    await client.post(
        "/api/complaints",
        json={
            "text": "Frequent voltage drops burning home electronics",
            "location": "Sector G-11, Islamabad",
        },
    )

    response = await client.get("/api/meta/providers")
    assert response.status_code == 200
    data = response.json()
    assert "active_provider" in data
    assert "recent_outcomes" in data
    assert isinstance(data["recent_outcomes"], list)


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """GET /metrics returns Prometheus format text."""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "# HELP" in response.text
    assert "# TYPE" in response.text
