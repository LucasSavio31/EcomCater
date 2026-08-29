"""Fixtures de teste. Requer um Postgres acessível (o serviço `db` do compose).

`make test` roda dentro do container `api` com `API_ENV=test`; o schema é
recriado a cada sessão a partir de `Base.metadata`.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.bootstrap import discover_modules
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base

discover_modules()

TEST_DB_URL = settings.database_url  # usa o mesmo banco; schema é dropado/recriado


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB_URL, poolclass=None)
    async with eng.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client, db) -> str:
    from app.core.security import hash_password
    from app.modules.admin.models import AdminUser

    db.add(
        AdminUser(
            email="root@test.local",
            name="Root",
            password_hash=hash_password("supersecret1"),
            role="super_admin",
            must_change_password=False,
        )
    )
    await db.commit()
    r = await client.post(
        "/api/admin/auth/login",
        json={"email": "root@test.local", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def auth_headers():
    def _make(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _make
