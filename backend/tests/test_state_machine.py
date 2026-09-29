"""Tests for complaint lifecycle state machine and status transition rules."""

import pytest


@pytest.mark.asyncio
async def test_valid_status_transitions_open_to_in_progress_to_resolved(client):
    """open -> in_progress -> resolved is a valid transition path."""
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Garbage dump near main hospital entrance needs removal",
            "location": "Hospital Road, Rawalpindi",
        },
    )
    cid = create_res.json()["id"]

    # 1. open -> in_progress
    patch1 = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "in_progress"},
    )
    assert patch1.status_code == 200
    assert patch1.json()["status"] == "in_progress"

    # 2. in_progress -> resolved
    patch2 = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "resolved"},
    )
    assert patch2.status_code == 200
    assert patch2.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_valid_status_transition_open_to_rejected(client):
    """open -> rejected is a valid transition."""
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Irrelevant noise complaint about neighbor talking softly",
            "location": "Sector F-10, Islamabad",
        },
    )
    cid = create_res.json()["id"]

    patch = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "rejected"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_invalid_transition_open_to_resolved_returns_409(client):
    """Direct transition open -> resolved is invalid and returns 409 naming the transition."""
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Broken water pipeline running through sector G-8",
            "location": "G-8/2, Islamabad",
        },
    )
    cid = create_res.json()["id"]

    patch = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "resolved"},
    )
    assert patch.status_code == 409
    data = patch.json()
    assert data["error"] == "invalid_transition"
    assert data["from"] == "open"
    assert data["to"] == "resolved"


@pytest.mark.asyncio
async def test_terminal_state_resolved_cannot_be_changed(client):
    """Resolved status is terminal; attempting any transition returns 409."""
    create_res = await client.post(
        "/api/complaints",
        json={
            "text": "Dead animal near residential park causing foul smell",
            "location": "Park Road, Islamabad",
        },
    )
    cid = create_res.json()["id"]

    # Advance to in_progress then resolved
    await client.patch(f"/api/complaints/{cid}/status", json={"status": "in_progress"})
    await client.patch(f"/api/complaints/{cid}/status", json={"status": "resolved"})

    # Attempt to reopen
    patch_fail = await client.patch(
        f"/api/complaints/{cid}/status",
        json={"status": "in_progress"},
    )
    assert patch_fail.status_code == 409
    data = patch_fail.json()
    assert data["error"] == "invalid_transition"
    assert data["from"] == "resolved"
    assert data["to"] == "in_progress"
