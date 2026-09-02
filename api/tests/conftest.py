"""Fixtures de teste.

SEGURANÇA: a suíte roda num banco **separado** do de desenvolvimento. O nome do
banco de teste é `<db>_test` (ou o que estiver em `TEST_DATABASE_URL`). Se, por
qualquer motivo, a URL de teste apontar para o mesmo banco do dev, a coleta é
abortada — o `drop_all`/`create_all` abaixo jamais deve rodar contra o dev.
O banco de teste é criado automaticamente se não existir.
"""
from __future__ import annotations

import os

# Marca o ambiente ANTES de qualquer import de `app.*` (o settings é cacheado):
# desliga rate limit, e-mails reais, etc.
os.environ.setdefault("API_ENV", "test")

from collections.abc import AsyncGenerator  # noqa: E402
from urllib.parse import urlparse, urlunparse  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.bootstrap import discover_modules  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

discover_modules()


def _derive_test_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    parts = urlparse(settings.database_url)
    db_name = parts.path.lstrip("/") or "ecom"
    if db_name.endswith("_test"):
        return settings.database_url
    return urlunparse(parts._replace(path=f"/{db_name}_test"))


TEST_DB_URL = _derive_test_url()

# --- trava de segurança: nunca rodar contra o banco de desenvolvimento --------
if settings.database_url == TEST_DB_URL and not urlparse(TEST_DB_URL).path.rstrip("/").endswith("_test"):
    raise RuntimeError(
        "ABORTADO: a suíte de testes apagaria o banco de desenvolvimento.\n"
        f"  DATABASE_URL dev  = {settings.database_url}\n"
        f"  URL de teste      = {TEST_DB_URL}\n"
        "Defina TEST_DATABASE_URL para um banco cujo nome termina em '_test'."
    )


async def _ensure_test_database() -> None:
    """Cria o banco de teste se ele ainda não existir (conecta na base `postgres`)."""
    import asyncpg  # driver já usado pelo SQLAlchemy async

    parts = urlparse(TEST_DB_URL.replace("postgresql+asyncpg", "postgresql"))
    target_db = parts.path.lstrip("/")
    admin_conn = await asyncpg.connect(
        host=parts.hostname, port=parts.port or 5432,
        user=parts.username, password=parts.password, database="postgres",
    )
    try:
        exists = await admin_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target_db)
        if not exists:
            await admin_conn.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        await admin_conn.close()


_schema_ready = False


@pytest_asyncio.fixture
async def engine():
    """Engine por teste (evita conflito de event loop no pytest-asyncio 1.x no
    Windows). O schema é (re)criado só uma vez por sessão."""
    global _schema_ready
    await _ensure_test_database()
    eng = create_async_engine(TEST_DB_URL, poolclass=None)

    # os subscribers do event bus (e-mail de pedido, leads, saúde) abrem a
    # própria sessão via `SessionLocal` — como cada módulo fez
    # `from app.core.database import SessionLocal`, reaponta a cópia de TODOS
    # os módulos `app.*` pro banco de teste enquanto a fixture viver.
    import sys

    import app.core.database as _db_mod

    _orig_session_local = _db_mod.SessionLocal
    _test_maker = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    _patched_mods = [
        m
        for name, m in list(sys.modules.items())
        if name.startswith("app.") and getattr(m, "SessionLocal", None) is _orig_session_local
    ]
    for m in _patched_mods:
        m.SessionLocal = _test_maker
    _db_mod.SessionLocal = _test_maker

    if not _schema_ready:
        async with eng.begin() as conn:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS citext")
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS unaccent")
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _schema_ready = True
    yield eng
    for m in _patched_mods:
        m.SessionLocal = _orig_session_local
    _db_mod.SessionLocal = _orig_session_local
    # isola os testes: zera todas as tabelas ao fim de cada um
    try:
        async with eng.begin() as conn:
            await conn.exec_driver_sql(
                "TRUNCATE TABLE "
                + ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
                + " RESTART IDENTITY CASCADE"
            )
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(engine, db) -> AsyncGenerator[AsyncClient, None]:
    # Uma sessão nova POR REQUISIÇÃO, como em produção (o `get_db` real). Usar a
    # mesma sessão do teste em todas as requisições mascara bugs de identity-map.
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

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
            email="root@test.example",
            name="Root",
            password_hash=hash_password("supersecret1"),
            role="super_admin",
            must_change_password=False,
        )
    )
    await db.commit()
    r = await client.post(
        "/api/admin/auth/login",
        json={"email": "root@test.example", "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def auth_headers():
    def _make(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _make
