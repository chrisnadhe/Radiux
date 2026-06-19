"""Integration tests untuk NAS — register dan verifikasi enkripsi secret."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.radius_core import NasCore
from app.services.nas_service import decrypt_secret


@pytest.mark.integration
class TestNasIntegration:
    """Test pendaftaran NAS dengan PostgreSQL sungguhan."""

    async def test_create_nas_encrypts_secret(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
    ) -> None:
        """POST /api/v1/nas harus mendaftarkan NAS dan mengenkripsi shared_secret."""
        plaintext_secret = "MySuperSecret123!"
        payload = {
            "nasname": "192.168.100.1",
            "shortname": "router-pusat",
            "nas_type": "mikrotik",
            "ports": 1700,
            "shared_secret": plaintext_secret,
            "description": "Router Utama",
            "tenant_id": None,  # Superadmin
        }

        resp = await int_client.post(
            "/api/v1/nas",
            json=payload,
            cookies=auth_cookies,
        )
        assert resp.status_code == 201

        # Verifikasi data di NasCore
        result = await db_session.execute(select(NasCore).where(NasCore.nasname == "192.168.100.1"))
        nas_core = result.scalar_one_or_none()
        assert nas_core is not None

        # Secret di DB harus terenkripsi (tidak sama dengan plaintext)
        assert nas_core.secret != plaintext_secret

        # Jika di-dekripsi, nilainya harus sama dengan plaintext
        decrypted = decrypt_secret(nas_core.secret)
        assert decrypted == plaintext_secret

    async def test_create_nas_duplicate_nasname_returns_409(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
    ) -> None:
        """Membuat NAS dengan nasname yang sama harus return 409."""
        payload = {
            "nasname": "10.10.10.1",
            "shortname": "router-cabang",
            "nas_type": "mikrotik",
            "shared_secret": "secret",
            "tenant_id": None,
        }

        # Buat pertama kali
        resp1 = await int_client.post("/api/v1/nas", json=payload, cookies=auth_cookies)
        assert resp1.status_code == 201

        # Buat kedua kali
        resp2 = await int_client.post("/api/v1/nas", json=payload, cookies=auth_cookies)
        assert resp2.status_code == 409
