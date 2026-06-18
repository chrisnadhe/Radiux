"""Unit tests untuk health check endpoint.

Memverifikasi:
- GET /health → 200 OK
- Response body berisi {"status": "ok", "version": "0.1.0"}
- Content-Type: application/json
"""

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestHealthCheck:
    """Test suite untuk endpoint GET /health."""

    async def test_health_returns_200(self, async_client: AsyncClient) -> None:
        """Health check harus return status 200 OK."""
        response = await async_client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_json(self, async_client: AsyncClient) -> None:
        """Health check harus return Content-Type: application/json."""
        response = await async_client.get("/health")
        assert "application/json" in response.headers["content-type"]

    async def test_health_body_status_ok(self, async_client: AsyncClient) -> None:
        """Health check harus return field 'status' bernilai 'ok'."""
        response = await async_client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    async def test_health_body_has_version(self, async_client: AsyncClient) -> None:
        """Health check harus menyertakan field 'version'."""
        response = await async_client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"

    async def test_health_no_auth_required(self, async_client: AsyncClient) -> None:
        """Health check harus bisa diakses tanpa autentikasi."""
        # Pastikan tidak ada cookie/token apapun
        response = await async_client.get(
            "/health",
            headers={},
            cookies={},
        )
        assert response.status_code == 200

    async def test_root_redirects_to_login(self, async_client: AsyncClient) -> None:
        """Root URL (/) harus redirect ke /login jika belum autentikasi."""
        response = await async_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_login_page_returns_200(self, async_client: AsyncClient) -> None:
        """Halaman /login harus return HTML 200 dan memuat nama aplikasi."""
        response = await async_client.get("/login")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Radiux" in response.text
