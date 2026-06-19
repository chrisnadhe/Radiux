"""Integration tests untuk customers CRUD — ke PostgreSQL sungguhan."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customers import Customer
from app.models.tenants import Tenant


@pytest.mark.integration
class TestCustomersIntegration:
    """Test CRUD customer dengan PostgreSQL sungguhan."""

    async def test_list_customers_returns_200(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
    ) -> None:
        """GET /api/v1/customers harus mengembalikan 200 dengan pagination."""
        resp = await int_client.get("/api/v1/customers", cookies=auth_cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_customers_without_auth_returns_401(self, int_client: AsyncClient) -> None:
        """Request tanpa auth harus return 401."""
        resp = await int_client.get("/api/v1/customers")
        assert resp.status_code == 401

    async def test_create_customer_persists_to_db(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """POST /api/v1/customers harus menyimpan customer ke DB."""
        payload = {
            "full_name": "Budi Santoso",
            "radius_username": "budi.santoso.test",
            "radius_password": "SecretPass123",
            "tenant_id": test_tenant.id,
        }
        resp = await int_client.post(
            "/api/v1/customers",
            json=payload,
            cookies=auth_cookies,
        )
        assert resp.status_code == 201
        data = resp.json()
        customer_id = data["id"]

        # Verifikasi langsung di DB
        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        assert customer is not None
        assert customer.full_name == "Budi Santoso"
        assert customer.radius_username == "budi.santoso.test"
        assert customer.tenant_id == test_tenant.id

    async def test_create_customer_duplicate_username_returns_409(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Membuat customer dengan radius_username yang sama harus return 409."""
        payload = {
            "full_name": "User Pertama",
            "radius_username": "user.duplicate.test",
            "radius_password": "SecretPass123",
            "tenant_id": test_tenant.id,
        }
        # Buat pertama kali
        resp1 = await int_client.post("/api/v1/customers", json=payload, cookies=auth_cookies)
        assert resp1.status_code == 201

        # Buat kedua kali dengan username yang sama
        payload["full_name"] = "User Kedua"
        resp2 = await int_client.post("/api/v1/customers", json=payload, cookies=auth_cookies)
        assert resp2.status_code == 409

    async def test_update_customer_changes_db(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """PATCH /api/v1/customers{id} harus memperbarui data di DB."""
        # Buat customer dulu
        create_resp = await int_client.post(
            "/api/v1/customers",
            json={
                "full_name": "Nama Lama",
                "radius_username": "user.update.test",
                "radius_password": "SecretPass123",
                "tenant_id": test_tenant.id,
            },
            cookies=auth_cookies,
        )
        assert create_resp.status_code == 201
        customer_id = create_resp.json()["id"]

        # Update nama
        update_resp = await int_client.patch(
            f"/api/v1/customers/{customer_id}",
            json={"full_name": "Nama Baru"},
            cookies=auth_cookies,
        )
        assert update_resp.status_code == 200

        # Verifikasi di DB
        db_session.expire_all()
        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one()
        assert customer.full_name == "Nama Baru"

    async def test_delete_customer_removes_from_db(
        self,
        int_client: AsyncClient,
        auth_cookies: dict,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """DELETE /api/v1/customers{id} harus menghapus customer dari DB."""
        # Buat customer dulu
        create_resp = await int_client.post(
            "/api/v1/customers",
            json={
                "full_name": "User Hapus",
                "radius_username": "user.delete.test",
                "radius_password": "SecretPass123",
                "tenant_id": test_tenant.id,
            },
            cookies=auth_cookies,
        )
        assert create_resp.status_code == 201
        customer_id = create_resp.json()["id"]

        # Hapus
        del_resp = await int_client.delete(
            f"/api/v1/customers/{customer_id}",
            cookies=auth_cookies,
        )
        assert del_resp.status_code == 204

        # Verifikasi tidak ada di DB
        db_session.expire_all()
        result = await db_session.execute(select(Customer).where(Customer.id == customer_id))
        assert result.scalar_one_or_none() is None
