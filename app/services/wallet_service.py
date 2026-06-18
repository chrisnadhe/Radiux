"""Service layer untuk manajemen Wallet dan transaksi Reseller."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenants import Tenant
from app.models.wallet_transactions import TransactionType, WalletTransaction


class InsufficientBalanceError(Exception):
    """Exception dilempar ketika saldo reseller tidak cukup."""

    pass


async def add_balance(
    db: AsyncSession, tenant_id: int, amount: float | Decimal, reference: str | None = None, notes: str | None = None
) -> WalletTransaction:
    """Menambah saldo reseller (Top Up)."""
    return await _process_transaction(db, tenant_id, TransactionType.TOPUP, amount, reference, notes)


async def deduct_balance(
    db: AsyncSession, tenant_id: int, amount: float | Decimal, reference: str | None = None, notes: str | None = None
) -> WalletTransaction:
    """Memotong saldo reseller (Deduction).

    Akan melempar InsufficientBalanceError jika saldo tidak cukup.
    """
    return await _process_transaction(db, tenant_id, TransactionType.DEDUCTION, amount, reference, notes)


async def _process_transaction(
    db: AsyncSession,
    tenant_id: int,
    transaction_type: TransactionType,
    amount: float | Decimal,
    reference: str | None = None,
    notes: str | None = None,
) -> WalletTransaction:
    """Internal helper untuk memproses perubahan saldo secara transaksional."""

    amount_decimal = Decimal(str(amount))
    if amount_decimal <= 0:
        raise ValueError("Amount transaksi harus lebih dari 0")

    # Ambil tenant dengan lock untuk mencegah race condition
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id).with_for_update())
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} tidak ditemukan")

    balance_before = Decimal(str(tenant.balance))

    if transaction_type == TransactionType.TOPUP:
        balance_after = balance_before + amount_decimal
    else:  # DEDUCTION
        if balance_before < amount_decimal:
            raise InsufficientBalanceError(
                f"Saldo tidak cukup. Saldo saat ini: {balance_before}, dibutuhkan: {amount_decimal}"
            )
        balance_after = balance_before - amount_decimal

    # Update balance tenant
    tenant.balance = float(balance_after)

    # Catat history transaksi
    trx = WalletTransaction(
        tenant_id=tenant_id,
        transaction_type=transaction_type,
        amount=amount_decimal,
        balance_before=balance_before,
        balance_after=balance_after,
        reference=reference,
        notes=notes,
    )
    db.add(trx)
    await db.flush()  # Pastikan ter-flush ke DB (belum commit agar bisa gabung di outer transaction)

    return trx
