"""Complaint endpoints — thin HTTP layer only.

POST   /api/complaints             → validate → triage → persist → 201
GET    /api/complaints/{id}        → 200 / 404
GET    /api/complaints             → paginated, filterable list
PATCH  /api/complaints/{id}/status → enforce state machine → 200 / 409
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.database import get_db
from app.models.complaint import Category, Priority, Status
from app.providers.rate_limiter import check_rate_limit
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintResponse,
    PaginatedComplaints,
    StatusUpdate,
)
from app.services import complaint_service
from app.services.complaint_service import InvalidTransition

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", status_code=201, response_model=ComplaintResponse)
async def create_complaint(
    payload: ComplaintCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate → triage → persist. 201. 400 on validation. 429 on rate limit."""
    # Rate limiting by client IP (respecting X-Forwarded-For if behind proxy/Ingress)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"
    retry_after = await check_rate_limit(client_ip)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    complaint = await complaint_service.create_complaint(db, payload)

    return ComplaintResponse.model_validate(complaint, from_attributes=True)


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """200 / 404."""
    complaint = await complaint_service.get_complaint(db, complaint_id)
    if complaint is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found"},
        )
    return ComplaintResponse.model_validate(complaint, from_attributes=True)


@router.get("", response_model=PaginatedComplaints)
async def list_complaints(
    category: Category | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    status: Status | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable list."""
    items, total = await complaint_service.list_complaints(
        db,
        category=category,
        priority=priority,
        status=status,
        page=page,
        page_size=page_size,
    )
    return PaginatedComplaints(
        items=[ComplaintResponse.model_validate(c, from_attributes=True) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_status(
    complaint_id: uuid.UUID,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Enforce the state machine. Invalid transition → 409."""
    try:
        complaint = await complaint_service.update_status(db, complaint_id, payload.status)
    except InvalidTransition as exc:
        return JSONResponse(
            status_code=409,
            content={
                "error": "invalid_transition",
                "from": exc.from_status.value,
                "to": exc.to_status.value,
            },
        )

    if complaint is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found"},
        )

    return ComplaintResponse.model_validate(complaint, from_attributes=True)
