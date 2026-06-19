"""Integration tests untuk Audit Log."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_users import AdminUser
from app.models.audit_logs import AuditLog


@pytest.mark.integration
class TestAuditIntegration:
    """Test audit logging dengan PostgreSQL sungguhan."""

    async def test_audit_log_created_on_login(
        self,
        int_client: AsyncClient,
        db_session: AsyncSession,
        superadmin_user: AdminUser,
    ) -> None:
        """Login sukses harus mencatat LOGIN_SUCCESS di tabel audit_logs."""
        # Pastikan tabel kosong / bersih dari sesi login user ini
        # Karena rollback per test, kita bisa hitung dari awal
        await db_session.execute(text("DELETE FROM audit_logs WHERE action = 'LOGIN_SUCCESS'"))
        await db_session.commit()

        resp = await int_client.post(
            "/api/v1/auth/login",
            json={"username": superadmin_user.username, "password": "TestPass123!"},
        )
        assert resp.status_code == 200

        # Verifikasi log di DB
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == superadmin_user.id).where(AuditLog.action == "LOGIN_SUCCESS")
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.ip_address is None or isinstance(log.ip_address, str)

    async def test_audit_log_created_on_nas_create(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
        superadmin_user: AdminUser,
    ) -> None:
        """Mendaftarkan NAS harus mencatat CREATE_NAS di audit_logs."""
        payload = {
            "nasname": "192.168.10.1",
            "shortname": "router-audit",
            "nas_type": "mikrotik",
            "shared_secret": "secret",
            "tenant_id": None,
        }
        resp = await int_client.post("/api/v1/nas", json=payload, cookies=auth_cookies)
        assert resp.status_code == 201

        # Verifikasi log di DB
        result = await db_session.execute(
            select(AuditLog).where(AuditLog.user_id == superadmin_user.id).where(AuditLog.action == "CREATE_NAS")
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        log = logs[-1]  # Ambil yang terbaru
        assert log.table_name == "nas_ext"
        assert log.details["nasname"] == "192.168.10.1"
