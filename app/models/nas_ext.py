"""Model NasExt — data tambahan NAS di luar skema inti FreeRADIUS.

Tabel NAS inti FreeRADIUS (`nas`) hanya menyimpan field minimal untuk
kebutuhan rlm_sql. NasExt menyimpan metadata tambahan: vendor info,
tenant scope, dan referensi ke nas_core.nasname.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NasExt(Base):
    """Ekstensi data NAS — vendor, tenant, dan metadata tambahan.

    Relasi ke NAS inti FreeRADIUS via nasname (bukan ID, karena FreeRADIUS
    tidak mengenal FK antar tabel inti ke ekstensi Radiux).
    """

    __tablename__ = "nas_ext"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Referensi ke nas.nasname (string-based, bukan FK ke kolom ID)
    nasname: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    # Vendor profile — akan diisi Phase 2 (saat tabel nas_vendor_profiles ada)
    # vendor_profile_id: Mapped[int | None] = mapped_column(...)
    vendor: Mapped[str] = mapped_column(String(64), nullable=False, default="generic")

    # Lokasi / label untuk tampilan di UI
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Tenant scope — NULL berarti NAS dikelola superadmin (shared)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="SET NULL"),
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

    def __repr__(self) -> str:
        return f"<NasExt id={self.id} nasname={self.nasname!r} vendor={self.vendor!r}>"
