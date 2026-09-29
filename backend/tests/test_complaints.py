"""Tests for complaint endpoints: creation, validation, querying, and stats."""

import pytest
import uuid


@pytest.mark.asyncio
async def test_create_complaint_success(client):
    """POST /api/complaints creates a complaint and returns 201 with triage details."""
    payload = {
        "text": "Water pipe has burst on Main Street and is flooding the road since morning",
        "location": "Main Street, Sector F-6, Islamabad",
        "reporter_contact": "0300-1234567",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["text"] == payload["text"]
    assert data["location"] == payload["location"]
    assert data["category"] == "water"
    assert data["status"] == "open"
    assert "triaged_by" in data
    assert "triage_latency_ms" in data


@pytest.mark.asyncio
async def test_create_complaint_validation_error_text_too_short(client):
    """POST /api/complaints with text < 10 chars returns 400 with field error."""
    payload = {
        "text": "Too short",
        "location": "Main Street, Islamabad",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "errors" in data
    fields = [err["field"] for err in data["errors"]]
    assert any("text" in f for f in fields)


@pytest.mark.asyncio
async def test_create_complaint_validation_error_missing_location(client):
    """POST /api/complaints with missing location returns 400."""
    payload = {
        "text": "Water pipeline is severely damaged and leaking everywhere",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "errors" in data
    fields = [err["field"] for err in data["errors"]]
    assert any("location" in f for f in fields)


@pytest.mark.asyncio
async def test_get_complaint_by_id(client):
    """GET /api/complaints/{id} returns 200 for existing and 404 for missing."""
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Streetlights not working on Road 4, very dark at night",
            "location": "Road 4, G-10, Islamabad",
        },
    )
    assert create_res.status_code == 201
    cid = create_res.json()["id"]

    # 200 for existing
    get_res = await client.get(f"/api/complaints/{cid}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == cid
    assert get_res.json()["category"] == "streetlights"

    # 404 for non-existent
    non_existent = str(uuid.uuid4())
    not_found_res = await client.get(f"/api/complaints/{non_existent}")
    assert not_found_res.status_code == 404
    assert not_found_res.json()["error"] == "not_found"


@pytest.mark.asyncio
async def test_list_complaints_pagination_and_filtering(client):
    """GET /api/complaints supports pagination and category/priority filters."""
    # Create water complaint
    await client.post(
        "/api/complaints",
        json={
            "text": "Water leakage from overhead supply tank near house 12",
            "location": "House 12, Street 3, Lahore",
        },
    )
    # Create electricity complaint
    await client.post(
        "/api/complaints",
        json={
            "text": "Transformer spark and power outage in market square",
            "location": "Market Square, Rawalpindi",
        },
    )

    # List all
    res_all = await client.get("/api/complaints?page=1&page_size=10")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] >= 2
    assert len(data_all["items"]) >= 2

    # Filter by category
    res_water = await client.get("/api/complaints?category=water")
    assert res_water.status_code == 200
    data_water = res_water.json()
    assert all(item["category"] == "water" for item in data_water["items"])


@pytest.mark.asyncio
async def test_get_stats_endpoint(client):
    """GET /api/stats returns category and priority aggregates."""
    await client.post(
        "/api/complaints",
        json={
            "text": "Potholes everywhere on highway causing severe accidents",
            "location": "GT Road, Gujar Khan",
        },
    )
    res = await client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "by_category" in data
    assert "by_priority" in data
    assert "total" in data
    assert data["total"] >= 1
    assert "X-Cache" in res.headers


@pytest.mark.asyncio
async def test_create_complaint_resilience_when_provider_raises(client, monkeypatch):
    """MANDATORY SPEC TEST: Given a triage provider that always raises an exception,

    POST /api/complaints still returns 201 with triaged_by == 'rules:fallback' (never 500).
    """
    class AlwaysFailingProvider:
        name: str = "failing_mock"

        async def triage(self, text: str, location: str):
            raise RuntimeError("Upstream LLM / AI service is completely down")

    from app.services import complaint_service
    monkeypatch.setattr(complaint_service, "_get_provider", lambda: AlwaysFailingProvider())

    payload = {
        "text": "Electric wires sparking with severe danger of fire near transformer",
        "location": "Sector I-10, Islamabad",
    }
    response = await client.post("/api/complaints", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["triaged_by"] == "rules:fallback"
    assert data["category"] == "electricity"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_stats_cache_header_hit_miss_and_invalidation(client):
    """Verify X-Cache transitions: MISS on fresh call, HIT on repeat, and invalidation on POST."""
    # Ensure at least 1 complaint
    await client.post(
        "/api/complaints",
        json={
            "text": "Pipeline leakage flooding residential avenue sidewalk",
            "location": "Avenue 3, Islamabad",
        },
    )

    # First fetch -> MISS or HIT depending on prior tests, let's invalidate first via POST
    await client.post(
        "/api/complaints",
        json={
            "text": "Another fresh complaint to trigger stats cache invalidation",
            "location": "Avenue 4, Islamabad",
        },
    )
    # Immediate fetch after POST should be MISS
    res1 = await client.get("/api/stats")
    assert res1.status_code == 200
    assert res1.headers.get("X-Cache") == "MISS"

    # Immediate second fetch should be HIT
    res2 = await client.get("/api/stats")
    assert res2.status_code == 200
    assert res2.headers.get("X-Cache") == "HIT"


@pytest.mark.asyncio
async def test_create_complaint_x_forwarded_for_rate_limit(client):
    """Verify rate limiter extracts and isolates IP from X-Forwarded-For header."""
    custom_ip = "203.0.113.195"
    payload = {
        "text": "Street light pole damaged and tilted dangerously on main road",
        "location": "Sector F-10, Islamabad",
    }
    headers = {"X-Forwarded-For": f"{custom_ip}, 10.0.0.1"}
    response = await client.post("/api/complaints", json=payload, headers=headers)
    assert response.status_code == 201

