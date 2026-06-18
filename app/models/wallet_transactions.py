"""Model WalletTransaction — histori topup atau pemotongan saldo tenant/reseller."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(enum.StrEnum):
    """Tipe transaksi dompet."""

    TOPUP = "topup"
    DEDUCTION = "deduction"


class WalletTransaction(Base):
    """Riwayat perubahan saldo reseller.
    Setiap transaksi generate voucher atau invoice akan tercatat sebagai DEDUCTION.
    Topup oleh superadmin akan tercatat sebagai TOPUP.
    """

    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="wallet_transaction_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Saldo sebelum transaksi (untuk audit)
    balance_before: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Saldo setelah transaksi (untuk audit)
    balance_after: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Referensi opsional (misal ID batch voucher atau ID tagihan)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<WalletTransaction id={self.id} type={self.transaction_type} amount={self.amount}>"
