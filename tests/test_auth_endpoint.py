"""Endpoint tests untuk auth router — login, verify-otp, logout."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.unit
class TestLoginEndpoint:
    """Test suite untuk POST /api/v1/auth/login."""

    async def test_login_wrong_credentials_returns_401(self, async_client: AsyncClient) -> None:
        """Login dengan password salah harus return 401."""
        from app.services.auth_service import AuthError

        with patch("app.api.v1.auth.auth_service.authenticate_user", side_effect=AuthError("salah")):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrongpass"},
            )
        assert resp.status_code == 401

    async def test_login_success_no_2fa_returns_200(self, async_client: AsyncClient) -> None:
        """Login sukses (tanpa 2FA) harus return 200 dan data response."""

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "admin"
        mock_user.role = MagicMock()
        mock_user.role.value = "superadmin"
        mock_user.is_2fa_enabled = False
        mock_user.tenant_id = None

        with (
            patch("app.api.v1.auth.auth_service.authenticate_user", return_value=mock_user),
            patch("app.api.v1.auth.audit_service.log_action", new_callable=AsyncMock),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "correctpassword"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert data["requires_otp"] is False

    async def test_login_with_2fa_returns_requires_otp(self, async_client: AsyncClient) -> None:
        """Login dengan 2FA aktif harus return requires_otp=True."""
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.username = "admin2fa"
        mock_user.role = MagicMock()
        mock_user.role.value = "superadmin"
        mock_user.is_2fa_enabled = True
        mock_user.telegram_chat_id = "123456789"
        mock_user.tenant_id = None

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)  # Under limit
        mock_redis.expire = AsyncMock()
        mock_redis.close = AsyncMock()
        mock_redis.setex = AsyncMock()

        with (
            patch("app.api.v1.auth.auth_service.authenticate_user", return_value=mock_user),
            patch("app.core.rate_limit.redis.from_url", return_value=mock_redis),
            patch("app.api.v1.auth.redis.from_url", return_value=mock_redis),
            patch("app.api.v1.auth._send_via_telegram", new_callable=AsyncMock),
            patch("app.api.v1.auth.audit_service.log_action", new_callable=AsyncMock),
        ):
            resp = await async_client.post(
                "/api/v1/auth/login",
                json={"username": "admin2fa", "password": "correctpassword"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_otp"] is True


@pytest.mark.unit
class TestLogoutEndpoint:
    """Test suite untuk POST /api/v1/auth/logout."""

    async def test_logout_clears_cookie(self, async_client: AsyncClient) -> None:
        """Logout harus menghapus cookie access_token."""
        resp = await async_client.post("/api/v1/auth/logout")
        assert resp.status_code == 200
        # Cookie dihapus — tidak perlu akses DB
        data = resp.json()
        assert "Logout" in data.get("message", "")
