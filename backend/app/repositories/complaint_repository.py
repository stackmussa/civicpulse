"""Complaint repository — ALL database queries live here, and nowhere else."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint import Category, Complaint, Priority, Status


async def create_complaint(
    db: AsyncSession,
    *,
    complaint_text: str,
    location: str,
    reporter_contact: str | None,
    category: Category,
    priority: Priority,
    ai_summary: str | None,
    triaged_by: str,
    triage_latency_ms: int,
) -> Complaint:
    """Insert a new complaint and return the flushed object."""
    complaint = Complaint(
        complaint_text=complaint_text,
        location=location,
        reporter_contact=reporter_contact,
        category=category,
        priority=priority,
        ai_summary=ai_summary,
        triaged_by=triaged_by,
        triage_latency_ms=triage_latency_ms,
    )
    db.add(complaint)
    await db.flush()
    await db.refresh(complaint)
    return complaint


async def get_complaint_by_id(db: AsyncSession, complaint_id: uuid.UUID) -> Complaint | None:
    """Fetch a single complaint by its UUID."""
    stmt = select(Complaint).where(Complaint.id == complaint_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_complaints(
    db: AsyncSession,
    *,
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Complaint], int]:
    """Return a (items, total) tuple for paginated listing."""
    stmt = select(Complaint)
    count_stmt = select(func.count()).select_from(Complaint)

    if category is not None:
        stmt = stmt.where(Complaint.category == category)
        count_stmt = count_stmt.where(Complaint.category == category)
    if priority is not None:
        stmt = stmt.where(Complaint.priority == priority)
        count_stmt = count_stmt.where(Complaint.priority == priority)
    if status is not None:
        stmt = stmt.where(Complaint.status == status)
        count_stmt = count_stmt.where(Complaint.status == status)

    stmt = stmt.order_by(Complaint.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return items, total


async def update_complaint_status(
    db: AsyncSession,
    complaint_id: uuid.UUID,
    new_status: Status,
) -> Complaint | None:
    """Update the status of a complaint and return the updated row."""
    stmt = (
        update(Complaint)
        .where(Complaint.id == complaint_id)
        .values(
            status=new_status,
            updated_at=datetime.now(UTC),
        )
        .returning(Complaint)
    )
    result = await db.execute(stmt)
    await db.flush()
    row = result.scalar_one_or_none()
    return row


async def get_stats(db: AsyncSession) -> dict:
    """Compute aggregate counts by category and priority."""
    cat_stmt = select(Complaint.category, func.count()).group_by(Complaint.category)
    pri_stmt = select(Complaint.priority, func.count()).group_by(Complaint.priority)
    total_stmt = select(func.count()).select_from(Complaint)

    cat_result = await db.execute(cat_stmt)
    pri_result = await db.execute(pri_stmt)
    total_result = await db.execute(total_stmt)

    return {
        "by_category": [{"category": row[0].value, "count": row[1]} for row in cat_result.all()],
        "by_priority": [{"priority": row[0].value, "count": row[1]} for row in pri_result.all()],
        "total": total_result.scalar() or 0,
    }


async def get_recent_triage_outcomes(db: AsyncSession, limit: int = 20) -> list[dict]:
    """Return the last *limit* triage outcomes for /api/meta/providers."""
    stmt = (
        select(
            Complaint.triaged_by,
            Complaint.triage_latency_ms,
        )
        .order_by(Complaint.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        {
            "provider": row[0],
            "latency_ms": row[1],
            "fallback": "fallback" in (row[0] or ""),
        }
        for row in result.all()
    ]
