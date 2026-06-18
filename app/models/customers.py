"""Model Customer — pelanggan end-user yang terdaftar di RADIUS."""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CustomerStatus(enum.StrEnum):
    """Status layanan customer."""

    ACTIVE = "active"
    SUSPENDED = "suspended"  # suspended manual atau karena expired/quota habis
    EXPIRED = "expired"
    INACTIVE = "inactive"


class Customer(Base):
    """Pelanggan end-user yang dikelola oleh tenant/reseller.

    Setiap customer memiliki satu username RADIUS (primary key di radcheck).
    Relasi ke tabel FreeRADIUS dilakukan via radius_username field, bukan FK
    (karena tabel inti FreeRADIUS tidak punya FK ke tabel ekstensi Radiux).

    ATURAN WAJIB: Semua query Customer HARUS di-scope dengan tenant_id.
    Lihat AGENT.md rule #2.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Username RADIUS — harus unik di seluruh sistem, dipakai di radcheck/radusergroup
    radius_username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Data pelanggan
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[CustomerStatus] = mapped_column(
        Enum(CustomerStatus, name="customer_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=CustomerStatus.ACTIVE,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Khusus untuk voucher
    is_voucher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    voucher_batch_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("voucher_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    voucher_password: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relasi ke paket (FK ke packages)
    package_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("packages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Tenant scope — WAJIB selalu ada (lihat AGENT.md rule #2)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Expiry — diisi saat customer aktif dengan paket validity tertentu
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821
    package: Mapped["Package | None"] = relationship("Package", back_populates="customers")  # type: ignore[name-defined]  # noqa: F821
    voucher_batch: Mapped["VoucherBatch | None"] = relationship("VoucherBatch", back_populates="vouchers")  # type: ignore[name-defined]  # noqa: F821

    def __repr__(self) -> str:
        return f"<Customer id={self.id} username={self.radius_username!r} status={self.status}>"
