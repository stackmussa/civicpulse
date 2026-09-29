"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _engine_kwargs(database_url: str) -> dict[str, int | bool]:
    kwargs: dict[str, int | bool] = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Type alias for four-layer boundary isolation (routes import DatabaseSession, not SQLAlchemy)
DatabaseSession = AsyncSession


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> bool:
    """Readiness probe health check — executes ping query without leaking SQL into routes."""
    from sqlalchemy import text

    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    return True
