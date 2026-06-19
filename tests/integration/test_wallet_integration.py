"""Integration tests untuk Wallet — transaksi topup/deduksi ke PostgreSQL sungguhan."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenants import Tenant
from app.models.wallet_transactions import TransactionType, WalletTransaction
from app.services import wallet_service


@pytest.mark.integration
class TestWalletIntegration:
    """Test transaksi saldo wallet dengan PostgreSQL sungguhan."""

    async def test_topup_updates_balance_in_db(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """add_balance harus menambah saldo tenant di DB dan mencatat transaksi."""
        initial_balance = float(test_tenant.balance)

        # Topup via service
        trx = await wallet_service.add_balance(
            db=db_session,
            tenant_id=test_tenant.id,
            amount=250_000,
            notes="Topup dari integration test",
        )
        assert trx.transaction_type == TransactionType.TOPUP
        assert trx.amount == 250_000
        trx_id = trx.id

        # Verifikasi saldo tenant
        tenant_id = test_tenant.id
        db_session.expire_all()
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()
        assert float(tenant.balance) == initial_balance + 250_000

        # Verifikasi log transaksi ada di DB
        trx_result = await db_session.execute(select(WalletTransaction).where(WalletTransaction.id == trx_id))
        saved_trx = trx_result.scalar_one_or_none()
        assert saved_trx is not None
        assert saved_trx.notes == "Topup dari integration test"

    async def test_deduct_insufficient_balance_throws_and_no_change(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> None:
        """Deduksi melebihi saldo harus throw error dan tidak mengubah saldo."""
        initial_balance = float(test_tenant.balance)

        # Coba deduksi lebih dari saldo
        amount_to_deduct = initial_balance + 100_000

        with pytest.raises(wallet_service.InsufficientBalanceError):
            await wallet_service.deduct_balance(
                db=db_session,
                tenant_id=test_tenant.id,
                amount=amount_to_deduct,
            )

        # Verifikasi saldo tidak berubah
        tenant_id = test_tenant.id
        db_session.expire_all()
        result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one()
        assert float(tenant.balance) == initial_balance
