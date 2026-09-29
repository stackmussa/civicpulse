"""Pydantic v2 schemas for complaint API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, Field

from app.models.complaint import Category, Priority, Status

# ── Request Schemas ──────────────────────────────────────────────────


class ComplaintCreate(BaseModel):
    """Body for POST /api/complaints."""

    text: str = Field(
        ..., min_length=10, max_length=2000, description="Complaint text"
    )
    location: str = Field(
        ..., min_length=3, max_length=200, description="Location"
    )
    reporter_contact: str | None = Field(
        default=None, max_length=200, description="Optional contact"
    )


class StatusUpdate(BaseModel):
    """Body for PATCH /api/complaints/{id}/status."""

    status: Status


# ── Response Schemas ─────────────────────────────────────────────────


class ComplaintResponse(BaseModel):
    """Single complaint in API responses."""

    id: uuid.UUID
    text: str = Field(validation_alias=AliasChoices("text", "complaint_text"))
    location: str
    reporter_contact: str | None = None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None = None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedComplaints(BaseModel):
    """Paginated list for GET /api/complaints."""

    items: list[ComplaintResponse]
    total: int
    page: int
    page_size: int


class StatsCategory(BaseModel):
    """Aggregate count for a single category."""

    category: str
    count: int


class StatsPriority(BaseModel):
    """Aggregate count for a single priority."""

    priority: str
    count: int


class StatsResponse(BaseModel):
    """Response for GET /api/stats."""

    by_category: list[StatsCategory]
    by_priority: list[StatsPriority]
    total: int


class TriageOutcome(BaseModel):
    """One entry in the provider-outcomes list."""

    provider: str
    latency_ms: int
    fallback: bool


class ProviderInfo(BaseModel):
    """Response for GET /api/meta/providers."""

    active_provider: str
    recent_outcomes: list[TriageOutcome]


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str = "ok"


class NotReadyResponse(BaseModel):
    error: str = "not_ready"
    failed: str


class ValidationErrorItem(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    errors: list[ValidationErrorItem]


class InvalidTransitionResponse(BaseModel):
    error: str = "invalid_transition"
    from_status: str = Field(alias="from")
    to_status: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class RateLimitResponse(BaseModel):
    error: str = "rate_limit_exceeded"
    retry_after: int
