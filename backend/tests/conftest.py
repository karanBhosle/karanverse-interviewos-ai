from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test-interviewos.db")
os.environ.setdefault("DATABASE_SYNC_URL", "sqlite:///./test-interviewos.db")
os.environ.setdefault("AUTHENTICATION_SECRET", "test-secret-test-secret-test-32b")
os.environ["AUTH_REQUIRED"] = "true"
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("UPLOAD_DIR", "./uploads-test")

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from pathlib import Path

from app.core.config import get_settings
from app.core.db import get_db, get_session_factory, init_models, reset_engine
from app.main import create_app

get_settings.cache_clear()
reset_engine()


@pytest.fixture
async def app():
    get_settings.cache_clear()
    reset_engine()
    db_path = Path("test-interviewos.db")
    if db_path.exists():
        db_path.unlink()
    await init_models()
    application = create_app()

    async def override_db() -> AsyncIterator[AsyncSession]:
        factory = get_session_factory()
        async with factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "karan@example.com", "password": "password12", "display_name": "Karan"},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
