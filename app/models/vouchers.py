"""Model VoucherBatch — pelacakan pembuatan massal voucher prabayar."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VoucherBatch(Base):
    """Batch pembuat voucher.
    Menyimpan history jumlah voucher yang digenerate dalam satu operasi.
    Detail vouchernya sendiri tersimpan di tabel customers.
    """

    __tablename__ = "voucher_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Prefix atau nama grup batch ini (misal "VC-JUNI-2026")
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Jumlah voucher yang diminta saat generate
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Format kode (misal panjang 6 karakter)
    length: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Catatan/deskripsi tambahan
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relasi ke Package
    package_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("packages.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Tenant scope
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821
    package: Mapped["Package"] = relationship("Package")  # type: ignore[name-defined]  # noqa: F821
    vouchers: Mapped[list["Customer"]] = relationship("Customer", back_populates="voucher_batch")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<VoucherBatch id={self.id} name={self.name!r} qty={self.quantity}>"
