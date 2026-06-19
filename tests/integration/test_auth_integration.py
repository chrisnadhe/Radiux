"""Integration tests untuk auth — login ke DB sungguhan."""

import pytest
from httpx import AsyncClient

from app.models.admin_users import AdminUser


@pytest.mark.integration
class TestLoginIntegration:
    """Test login dengan PostgreSQL sungguhan."""

    async def test_login_success_sets_cookie(self, int_client: AsyncClient, superadmin_user: AdminUser) -> None:
        """Login sukses harus mengembalikan 200 dan set cookie access_token."""
        resp = await int_client.post(
            "/api/v1/auth/login",
            json={"username": superadmin_user.username, "password": "TestPass123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == superadmin_user.username
        assert data["requires_otp"] is False
        assert "access_token" in resp.cookies

    async def test_login_wrong_password_returns_401(self, int_client: AsyncClient, superadmin_user: AdminUser) -> None:
        """Login dengan password salah harus return 401."""
        resp = await int_client.post(
            "/api/v1/auth/login",
            json={"username": superadmin_user.username, "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_user_returns_401(self, int_client: AsyncClient) -> None:
        """Login dengan username yang tidak ada di DB harus return 401."""
        resp = await int_client.post(
            "/api/v1/auth/login",
            json={"username": "useryangtidakada_xzy123", "password": "anypass"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_user_returns_401(
        self, int_client: AsyncClient, db_session, superadmin_user: AdminUser
    ) -> None:
        """Login dengan akun nonaktif harus return 401."""
        # Nonaktifkan user langsung di session
        superadmin_user.is_active = False
        await db_session.flush()

        resp = await int_client.post(
            "/api/v1/auth/login",
            json={"username": superadmin_user.username, "password": "TestPass123!"},
        )
        assert resp.status_code == 401

    async def test_logout_clears_session(self, int_client: AsyncClient, auth_cookies: dict) -> None:
        """Logout harus menghapus sesi dan cookie."""
        resp = await int_client.post("/api/v1/auth/logout", cookies=auth_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert "Logout" in data.get("message", "")
