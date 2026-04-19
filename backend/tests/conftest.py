import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Must be set before any app module is imported so pydantic-settings picks them up.
os.environ.setdefault("SECRET_KEY", "a" * 64)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

# ---------------------------------------------------------------------------
# Stub out optional ML / native dependencies that are not installed in the
# test environment (only present with `uv sync --extra ml`).
# ---------------------------------------------------------------------------
_ML_STUBS = [
    "numpy",
    "faster_whisper",
    "ctranslate2",
    "transformers",
    "aiortc",
    "av",
    "torch",
    "torchaudio",
    "sentencepiece",
]
for _mod in _ML_STUBS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# ---------------------------------------------------------------------------
# Async fixtures shared across test modules
# ---------------------------------------------------------------------------
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_async_engine(
        _TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Async DB session bound to the in-memory engine."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_engine):
    """AsyncClient wired to the FastAPI app with an in-memory DB and stubbed ML models."""
    from unittest.mock import patch

    from app.core.ratelimit import limiter
    from app.main import app

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    # Reset the in-process rate-limit storage so each test starts fresh.
    limiter._storage.reset()

    with (
        patch("app.main.STTPipeline", return_value=AsyncMock()),
        patch("app.main.NLLBTranslator", return_value=AsyncMock()),
        patch("app.main.init_db", new_callable=AsyncMock),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
