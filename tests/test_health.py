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

    async def test_root_returns_200(self, async_client: AsyncClient) -> None:
        """Root URL (/) harus return halaman HTML 200."""
        response = await async_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    async def test_root_contains_app_name(self, async_client: AsyncClient) -> None:
        """Halaman root harus mengandung nama aplikasi 'Radiux'."""
        response = await async_client.get("/")
        assert "Radiux" in response.text
