"""
Pytest configuration.
- Spins up tables in a separate test DB (talentbridge_test).
- Each test wraps in a savepoint that rolls back — no leakage between tests.
- Overrides Redis with fakeredis for fast, isolated tests.
"""
import os
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fakeredis.aioredis import FakeRedis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Point at test DB before importing app modules
_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://talentbridge:talentbridge_dev_password@localhost:5432/talentbridge_test",
)
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from app.db.base import Base
from app.main import create_app
import app.core.deps as deps_module  # noqa: E402 — patched below

# ---------------------------------------------------------------------------
# Engine / session fixtures
# ---------------------------------------------------------------------------

_test_engine = create_async_engine(_TEST_DB_URL, echo=False)
_TestSessionLocal = async_sessionmaker(bind=_test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once per session, drop on teardown."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Each test gets a session that rolls back via savepoint."""
    async with _test_engine.connect() as conn:
        await conn.begin()
        nested = await conn.begin_nested()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            if nested.is_active:
                await nested.rollback()
            await conn.rollback()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[FakeRedis, None]:
    r = FakeRedis()
    yield r
    await r.flushall()
    await r.aclose()


# ---------------------------------------------------------------------------
# App / HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, fake_redis: FakeRedis) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB and Redis overridden for isolation."""
    app = create_app()

    # Override FastAPI dependencies
    app.dependency_overrides[deps_module.get_db] = lambda: _override_db(db_session)
    app.dependency_overrides[deps_module.get_redis] = lambda: fake_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _override_db(session: AsyncSession):
    yield session
