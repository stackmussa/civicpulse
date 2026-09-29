"""SQLAlchemy ORM model for the complaints table."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""


class Category(str, enum.Enum):
    """Complaint category enum."""

    water = "water"
    electricity = "electricity"
    sanitation = "sanitation"
    roads = "roads"
    streetlights = "streetlights"
    other = "other"


class Priority(str, enum.Enum):
    """Complaint priority enum."""

    high = "high"
    normal = "normal"
    low = "low"


class Status(str, enum.Enum):
    """Complaint lifecycle status enum."""

    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


# ── Explicit state-machine transition table ──────────────────────────
# If target not in TRANSITIONS[current], the transition is invalid → 409
TRANSITIONS: dict[Status, set[Status]] = {
    Status.open: {Status.in_progress, Status.rejected},
    Status.in_progress: {Status.resolved, Status.rejected},
    Status.resolved: set(),      # terminal
    Status.rejected: set(),      # terminal
}


class Complaint(Base):
    """complaints table — single source of truth for municipal complaints."""

    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa_text("gen_random_uuid()"),
    )
    complaint_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    @property
    def text(self) -> str:
        return self.complaint_text

    location: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    reporter_contact: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    category: Mapped[Category] = mapped_column(
        Enum(Category, name="category_enum", create_constraint=False),
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="priority_enum", create_constraint=False),
        nullable=False,
    )
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status_enum", create_constraint=False),
        nullable=False,
        default=Status.open,
        server_default=sa_text("'open'"),
    )
    ai_summary: Mapped[str | None] = mapped_column(
        String(140),
        nullable=True,
    )
    triaged_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    triage_latency_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=sa_text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=sa_text("now()"),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        # DB-level check constraints as required by spec
        CheckConstraint(
            "length(complaint_text) BETWEEN 10 AND 2000",
            name="ck_complaint_text_length",
        ),
        CheckConstraint(
            "length(location) BETWEEN 3 AND 200",
            name="ck_location_length",
        ),
        CheckConstraint(
            "ai_summary IS NULL OR length(ai_summary) <= 140",
            name="ck_ai_summary_length",
        ),
        # Indexes justified by specific queries
        # ix_status_priority → serves GET /api/complaints?status=open&priority=high
        Index("ix_complaints_status_priority", "status", "priority"),
        # ix_created_at → serves default pagination ordering and stats time-window
        Index("ix_complaints_created_at", "created_at"),
    )
