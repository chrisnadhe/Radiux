"""Shared pytest fixtures untuk seluruh test suite Radiux.

CATATAN: env vars wajib di-set sebelum import apapun dari `app.*`
agar Settings tidak error karena field required tidak ada.
"""

import os

# Set env vars minimal yang dibutuhkan Settings sebelum import app
_TEST_SECRET = "test-secret-key-panjang-untuk-pytest-12345678901234567890"  # noqa: S105
os.environ.setdefault("SECRET_KEY", _TEST_SECRET)
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")  # noqa: S105
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    """Gunakan asyncio sebagai backend anyio."""
    return "asyncio"


@pytest.fixture
async def async_client() -> AsyncClient:
    """AsyncClient yang terhubung ke FastAPI app via ASGI transport.

    Tidak perlu server berjalan — langsung test ASGI app.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client
