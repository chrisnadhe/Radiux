"""Shared fixtures untuk integration tests Radiux.

PRASYARAT:
- PostgreSQL berjalan dan bisa diakses (via docker compose atau lokal)
- Redis berjalan di port 6379
- `uv run alembic upgrade head` sudah dijalankan

Jalankan dengan:
    uv run pytest -m integration -v
"""

import os
import sys
import uuid

from dotenv import load_dotenv

# Load real .env for integration tests
load_dotenv(override=True)

# Override only specific test env vars
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("POSTGRES_HOST", "127.0.0.1")

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.core.database import engine
from app.main import app
from app.models.admin_users import AdminRole, AdminUser
from app.models.tenants import Tenant, TenantStatus

# ---------------------------------------------------------------------------
# Session dengan ROLLBACK per-test (isolasi data)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def db_conn() -> AsyncConnection:
    """Buka satu koneksi DB dan mulai transaction + savepoint.

    Setiap test berjalan di nested transaction (SAVEPOINT) yang di-rollback
    setelah test selesai — data tidak pernah benar-benar ter-commit ke DB.
    """
    async with engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()  # SAVEPOINT

        yield conn

        await conn.rollback()  # Rollback semua perubahan test


@pytest.fixture(scope="function")
async def db_session(db_conn: AsyncConnection) -> AsyncSession:
    """AsyncSession yang terikat ke koneksi rollback-per-test."""
    session_factory = async_sessionmaker(bind=db_conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Override FastAPI get_db dependency
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def int_client(db_session: AsyncSession) -> AsyncClient:
    """AsyncClient yang terhubung ke app dengan DB session di-override.

    Setiap request dalam client ini memakai session yang sama
    (dan rollback-per-test).
    """
    from app.core.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
async def flush_redis() -> None:
    """Bersihkan redis sebelum setiap test untuk menghindari state bocor."""
    import redis.asyncio as redis

    from app.core.config import get_settings

    settings = get_settings()
    redis_conn = redis.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)
    await redis_conn.flushdb()
    await redis_conn.aclose()


# ---------------------------------------------------------------------------
# Fixtures: Tenant & Superadmin
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Buat tenant unik untuk isolasi data per-test."""
    uid = uuid.uuid4().hex[:8]
    tenant = Tenant(
        name=f"Test Tenant {uid}",
        slug=f"test-tenant-{uid}",
        status=TenantStatus.ACTIVE,
        balance=1_000_000.0,
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
async def superadmin_user(db_session: AsyncSession) -> AdminUser:
    """Buat superadmin via service langsung — tanpa bergantung pada data seed."""
    from app.core.security import get_password_hash

    uid = uuid.uuid4().hex[:8]
    user = AdminUser(
        username=f"superadmin_{uid}",
        email=f"superadmin_{uid}@test.local",
        hashed_password=get_password_hash("TestPass123!"),
        role=AdminRole.SUPERADMIN,
        is_active=True,
        tenant_id=None,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
async def auth_cookies(int_client: AsyncClient, superadmin_user: AdminUser) -> dict:
    """Login dan kembalikan cookies yang berisi access_token."""
    resp = await int_client.post(
        "/api/v1/auth/login",
        json={"username": superadmin_user.username, "password": "TestPass123!"},
    )
    assert resp.status_code == 200, f"Login fixture gagal: {resp.text}"
    return dict(resp.cookies)
