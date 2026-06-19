"""Unit tests untuk billing_service — record_payment dan generate invoice logic."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.customers import CustomerStatus
from app.models.invoices import InvoiceStatus
from app.services import billing_service


def _make_db() -> AsyncMock:
    """Buat mock AsyncSession."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.scalar = AsyncMock(return_value=None)
    db.scalars = AsyncMock()
    return db


def _make_invoice(status: InvoiceStatus = InvoiceStatus.UNPAID) -> MagicMock:
    """Buat mock Invoice."""
    inv = MagicMock()
    inv.status = status
    inv.paid_at = None
    return inv


def _make_customer(status: CustomerStatus = CustomerStatus.ACTIVE) -> MagicMock:
    """Buat mock Customer."""
    cust = MagicMock()
    cust.status = status
    return cust


@pytest.mark.unit
class TestRecordPayment:
    """Test suite untuk billing_service.record_payment()."""

    async def test_creates_payment_object(self) -> None:
        """record_payment harus membuat dan menyimpan objek Payment."""
        db = _make_db()
        # Tidak ada invoice dan customer yang suspended
        db.scalar = AsyncMock(return_value=None)

        await billing_service.record_payment(db, customer_id=1, amount=150_000, tenant_id=2)
        db.add.assert_called()
        db.commit.assert_awaited_once()

    async def test_marks_invoice_as_paid_when_invoice_id_given(self) -> None:
        """Jika invoice_id diberikan dan invoice masih UNPAID, statusnya harus PAID."""
        db = _make_db()
        invoice = _make_invoice(InvoiceStatus.UNPAID)
        customer = _make_customer(CustomerStatus.ACTIVE)

        # Kembalikan invoice saat query invoice, customer saat query customer
        db.scalar = AsyncMock(side_effect=[invoice, customer])

        await billing_service.record_payment(db, customer_id=1, amount=150_000, tenant_id=2, invoice_id=10)
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.paid_at is not None

    async def test_does_not_update_already_paid_invoice(self) -> None:
        """Invoice yang sudah PAID tidak boleh diubah lagi."""
        db = _make_db()
        invoice = _make_invoice(InvoiceStatus.PAID)
        customer = _make_customer(CustomerStatus.ACTIVE)
        db.scalar = AsyncMock(side_effect=[invoice, customer])

        await billing_service.record_payment(db, customer_id=1, amount=150_000, tenant_id=2, invoice_id=10)
        # Status tetap PAID, bukan berubah
        assert invoice.status == InvoiceStatus.PAID

    async def test_reactivates_suspended_customer_after_payment(self) -> None:
        """Customer yang SUSPENDED harus jadi ACTIVE setelah pembayaran."""
        db = _make_db()
        customer = _make_customer(CustomerStatus.SUSPENDED)
        # Tidak ada invoice — hanya ada customer
        db.scalar = AsyncMock(side_effect=[customer])

        await billing_service.record_payment(db, customer_id=1, amount=50_000, tenant_id=2)
        assert customer.status == CustomerStatus.ACTIVE

    async def test_active_customer_status_unchanged(self) -> None:
        """Customer yang sudah ACTIVE tidak berubah statusnya."""
        db = _make_db()
        customer = _make_customer(CustomerStatus.ACTIVE)
        db.scalar = AsyncMock(side_effect=[customer])

        await billing_service.record_payment(db, customer_id=1, amount=50_000, tenant_id=2)
        assert customer.status == CustomerStatus.ACTIVE


@pytest.mark.unit
class TestCreateManualInvoice:
    """Test suite untuk billing_service.create_manual_invoice()."""

    async def test_superadmin_tenant_skips_wallet_deduct(self) -> None:
        """tenant_id=1 (superadmin) tidak boleh memotong saldo wallet."""
        db = _make_db()

        with patch("app.services.billing_service.wallet_service.deduct_balance") as mock_deduct:
            await billing_service.create_manual_invoice(
                db,
                customer_id=1,
                amount=100_000,
                billing_period="June 2026",
                due_date=date.today() + timedelta(days=7),
                tenant_id=1,  # Superadmin
            )
            mock_deduct.assert_not_awaited()

    async def test_reseller_tenant_deducts_wallet(self) -> None:
        """tenant_id != 1 (reseller) harus memotong saldo wallet."""
        db = _make_db()

        with patch("app.services.billing_service.wallet_service.deduct_balance") as mock_deduct:
            mock_deduct.return_value = MagicMock()
            await billing_service.create_manual_invoice(
                db,
                customer_id=5,
                amount=200_000,
                billing_period="June 2026",
                due_date=date.today() + timedelta(days=7),
                tenant_id=2,  # Reseller
            )
            mock_deduct.assert_awaited_once()

    async def test_invoice_saved_to_db(self) -> None:
        """Invoice harus di-add ke session dan di-commit."""
        db = _make_db()

        with patch("app.services.billing_service.wallet_service.deduct_balance"):
            await billing_service.create_manual_invoice(
                db,
                customer_id=3,
                amount=50_000,
                billing_period="June 2026",
                due_date=date.today() + timedelta(days=7),
                tenant_id=1,
            )
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
