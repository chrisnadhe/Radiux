"""Model Invoice — tagihan bulanan untuk pelanggan pascabayar."""

import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceStatus(enum.StrEnum):
    """Status tagihan."""

    UNPAID = "unpaid"
    PAID = "paid"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Data tagihan bulanan pelanggan."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Nomor tagihan (misal INV-202606-0001)
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Relasi ke customer
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Periode tagihan (misal "Juni 2026" atau sekadar bulan/tahun angka)
    billing_period: Mapped[str] = mapped_column(String(64), nullable=False)

    # Tanggal jatuh tempo
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Total tagihan (diambil dari harga paket saat di-generate)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)

    # Status
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InvoiceStatus.UNPAID,
        index=True,
    )

    # Relasi ke tenant
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Tanggal lunas
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821
    customer: Mapped["Customer"] = relationship("Customer")  # type: ignore[name-defined]  # noqa: F821
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="invoice")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} status={self.status}>"
