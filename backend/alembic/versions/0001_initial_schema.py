"""0001 — Initial schema: complaints table with enums, indexes, constraints.

Revision ID: 0001
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgcrypto for gen_random_uuid()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create enum types
    category_enum = postgresql.ENUM(
        "water", "electricity", "sanitation", "roads", "streetlights", "other",
        name="category_enum",
        create_type=False,
    )
    priority_enum = postgresql.ENUM(
        "high", "normal", "low",
        name="priority_enum",
        create_type=False,
    )
    status_enum = postgresql.ENUM(
        "open", "in_progress", "resolved", "rejected",
        name="status_enum",
        create_type=False,
    )
    category_enum.create(op.get_bind(), checkfirst=True)
    priority_enum.create(op.get_bind(), checkfirst=True)
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "complaints",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("complaint_text", sa.Text(), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("reporter_contact", sa.String(200), nullable=True),
        sa.Column(
            "category",
            category_enum,
            nullable=False,
        ),
        sa.Column(
            "priority",
            priority_enum,
            nullable=False,
        ),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("ai_summary", sa.String(140), nullable=True),
        sa.Column("triaged_by", sa.String(50), nullable=False),
        sa.Column("triage_latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        # DB-level CHECK constraints
        sa.CheckConstraint(
            "char_length(complaint_text) BETWEEN 10 AND 2000",
            name="ck_complaint_text_length",
        ),
        sa.CheckConstraint(
            "char_length(location) BETWEEN 3 AND 200",
            name="ck_location_length",
        ),
        sa.CheckConstraint(
            "ai_summary IS NULL OR char_length(ai_summary) <= 140",
            name="ck_ai_summary_length",
        ),
    )

    # ix_complaints_status_priority — serves GET /api/complaints?status=open&priority=high
    # This is the dashboard's default filtered view, the highest-traffic query.
    op.create_index(
        "ix_complaints_status_priority",
        "complaints",
        ["status", "priority"],
    )

    # ix_complaints_created_at — serves default pagination ordering and
    # the stats aggregation's time-window queries.
    op.create_index(
        "ix_complaints_created_at",
        "complaints",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_complaints_created_at", table_name="complaints")
    op.drop_index("ix_complaints_status_priority", table_name="complaints")
    op.drop_table("complaints")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS status_enum")
    op.execute("DROP TYPE IF EXISTS priority_enum")
    op.execute("DROP TYPE IF EXISTS category_enum")
