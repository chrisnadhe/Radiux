"""Unit tests untuk wallet_service — topup dan deduksi saldo reseller."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.wallet_service import InsufficientBalanceError, add_balance, deduct_balance


def _make_tenant(balance: float) -> MagicMock:
    """Buat mock Tenant dengan saldo tertentu."""
    tenant = MagicMock()
    tenant.id = 1
    tenant.balance = balance
    return tenant


def _make_db(tenant: MagicMock) -> AsyncMock:
    """Buat mock AsyncSession yang mengembalikan tenant."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = tenant
    db.execute = AsyncMock(return_value=scalar_result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.unit
class TestAddBalance:
    """Test suite untuk wallet_service.add_balance()."""

    async def test_topup_increases_balance(self) -> None:
        """Topup harus menambah saldo tenant."""
        tenant = _make_tenant(balance=100_000.0)
        db = _make_db(tenant)

        await add_balance(db, tenant_id=1, amount=50_000)
        # Saldo tenant harus bertambah
        assert float(tenant.balance) == pytest.approx(150_000.0)

    async def test_topup_returns_transaction(self) -> None:
        """add_balance harus mengembalikan objek WalletTransaction."""

        tenant = _make_tenant(balance=0.0)
        db = _make_db(tenant)

        trx = await add_balance(db, tenant_id=1, amount=200_000)
        assert trx is not None
        db.add.assert_called_once()

    async def test_topup_zero_raises(self) -> None:
        """Topup dengan amount 0 harus raise ValueError."""
        tenant = _make_tenant(balance=100_000.0)
        db = _make_db(tenant)

        with pytest.raises(ValueError, match="Amount transaksi harus lebih dari 0"):
            await add_balance(db, tenant_id=1, amount=0)


@pytest.mark.unit
class TestDeductBalance:
    """Test suite untuk wallet_service.deduct_balance()."""

    async def test_deduct_decreases_balance(self) -> None:
        """Deduksi harus mengurangi saldo tenant."""
        tenant = _make_tenant(balance=100_000.0)
        db = _make_db(tenant)

        await deduct_balance(db, tenant_id=1, amount=30_000)
        assert float(tenant.balance) == pytest.approx(70_000.0)

    async def test_deduct_insufficient_balance_raises(self) -> None:
        """Deduksi lebih dari saldo harus raise InsufficientBalanceError."""
        tenant = _make_tenant(balance=10_000.0)
        db = _make_db(tenant)

        with pytest.raises(InsufficientBalanceError, match="Saldo tidak cukup"):
            await deduct_balance(db, tenant_id=1, amount=50_000)

    async def test_deduct_exact_balance_succeeds(self) -> None:
        """Deduksi tepat saldo yang tersisa harus berhasil."""
        tenant = _make_tenant(balance=50_000.0)
        db = _make_db(tenant)

        await deduct_balance(db, tenant_id=1, amount=50_000)
        assert float(tenant.balance) == pytest.approx(0.0)

    async def test_deduct_tenant_not_found_raises(self) -> None:
        """Deduksi untuk tenant yang tidak ada harus raise ValueError."""
        db = AsyncMock()
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=scalar_result)

        with pytest.raises(ValueError, match="Tenant .* tidak ditemukan"):
            await deduct_balance(db, tenant_id=9999, amount=1000)
