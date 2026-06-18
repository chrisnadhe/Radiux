"""Model Package — paket layanan internet (speed, kuota, harga, validity)."""

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PackageType(enum.StrEnum):
    """Tipe paket: prepaid (voucher) atau postpaid (invoice)."""

    PREPAID = "prepaid"
    POSTPAID = "postpaid"


class Package(Base):
    """Paket layanan internet yang bisa diassign ke customer.

    Saat package dibuat/diupdate, service akan sync atribut bandwidth
    ke tabel radgroupcheck/radgroupreply via group_name.
    """

    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # Nama grup RADIUS yang dipakai di radgroupcheck/radgroupreply/radusergroup
    group_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_type: Mapped[PackageType] = mapped_column(
        Enum(PackageType, name="package_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PackageType.PREPAID,
    )

    # Speed (Kbps) — 0 berarti unlimited
    speed_up_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speed_down_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Kuota (MB) — 0 berarti unlimited
    quota_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Validity (hari) — 0 berarti tidak ada expiry
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # Harga
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Tenant scope — NULL berarti paket milik superadmin (tersedia semua tenant)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant | None"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821
    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="package")  # type: ignore[name-defined]  # noqa: F821

    @property
    def speed_up_mbps(self) -> float:
        """Upload speed dalam Mbps."""
        return self.speed_up_kbps / 1000

    @property
    def speed_down_mbps(self) -> float:
        """Download speed dalam Mbps."""
        return self.speed_down_kbps / 1000

    def __repr__(self) -> str:
        return f"<Package id={self.id} name={self.name!r} group={self.group_name!r}>"
