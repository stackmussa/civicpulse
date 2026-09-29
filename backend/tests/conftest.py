"""Pytest fixtures for backend test suite.

Uses an in-memory SQLite database via aiosqlite and overrides the get_db dependency.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.complaint import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, in-memory async SQLite session per test."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test HTTP client with overridden get_db dependency."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


class MockRedis:
    """Fast, in-memory async Redis mock for test isolation."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def eval(self, script: str, numkeys: int, *args) -> int:
        return -1

    async def aclose(self) -> None:
        pass


@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """Provide isolated mock Redis instance for all tests."""
    r = MockRedis()

    async def _get_mock_redis():
        return r

    monkeypatch.setattr("app.providers.cache.get_redis", _get_mock_redis)
    monkeypatch.setattr("app.providers.rate_limiter.get_redis", _get_mock_redis)
    return r
