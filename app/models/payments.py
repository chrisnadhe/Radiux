"""Model Payment — pencatatan pembayaran pelanggan."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentMethod(enum.StrEnum):
    """Metode pembayaran."""

    CASH = "cash"
    TRANSFER = "transfer"
    # Bisa ditambah gateway (misal midtrans, xendit) di kemudian hari
    GATEWAY = "gateway"


class Payment(Base):
    """Rekaman pembayaran dari pelanggan."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Nomor tanda terima atau referensi (opsional)
    reference: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relasi ke customer
    customer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Relasi ke invoice (Opsional, karena prabayar mungkin bayar tanpa invoice formal)
    invoice_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PaymentMethod.CASH,
    )

    # Relasi ke tenant
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
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
    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="payments")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Payment {self.id} amount={self.amount} method={self.method}>"
