"""Model NasVendorProfile — profil vendor NAS untuk abstraksi atribut RADIUS.

Setiap NAS diasosiasikan dengan satu VendorProfile yang mendefinisikan:
- Atribut rate-limit yang digunakan (berbeda per vendor)
- Format nilai atribut rate-limit (mikrotik, bps, kbps, cisco_ios, dsb.)
- Atribut tambahan (untuk vendor yang butuh lebih dari satu atribut bandwidth)
"""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RateLimitFormat(enum.StrEnum):
    """Format nilai atribut rate-limit RADIUS per vendor.

    Nilai ini menentukan cara ``format_rate_limit()`` di vendor_profile_service
    menghitung string/angka yang dimasukkan ke radgroupreply.
    """

    # Mikrotik RouterOS: satu atribut "down_kbps k/up_kbps k"
    # Contoh: Mikrotik-Rate-Limit = "10240k/5120k"
    MIKROTIK = "mikrotik"

    # Satu atribut, nilai = download kbps
    # Contoh: Cambium-Canopy-Sustained-Downlink-Rate = "10240"
    KBPS_SINGLE_DOWN = "kbps_single_down"

    # Satu atribut, nilai = upload kbps
    # Contoh: Cambium-Canopy-Sustained-Uplink-Rate = "5120"
    KBPS_SINGLE_UP = "kbps_single_up"

    # Satu atribut, nilai = download dalam bps (kbps * 1000)
    # Contoh: WISPr-Bandwidth-Max-Down = "10240000"
    BPS_SINGLE_DOWN = "bps_single_down"

    # Satu atribut, nilai = upload dalam bps (kbps * 1000)
    # Contoh: WISPr-Bandwidth-Max-Up = "5120000"
    BPS_SINGLE_UP = "bps_single_up"

    # Cisco IOS/IOS-XE: dua Cisco-AVPair lcp:interface-config rate-limit
    # Contoh:
    #   Cisco-AVPair += "lcp:interface-config#1=rate-limit input 5120000 640000 640000 ..."
    #   Cisco-AVPair += "lcp:interface-config#2=rate-limit output 10240000 1280000 1280000 ..."
    CISCO_IOS = "cisco_ios"

    # Tidak ada rate-limit attribute (autentikasi saja / custom manual)
    NONE = "none"


class NasVendorProfile(Base):
    """Profil vendor NAS — mendefinisikan mapping atribut RADIUS per vendor.

    Profil bawaan (is_builtin=True) tidak bisa dihapus, namun atribut
    extra_group_reply_attrs dan is_active-nya bisa diubah admin.
    Admin bisa membuat profil kustom (is_builtin=False) untuk vendor lain.
    """

    __tablename__ = "nas_vendor_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Slug unik: "mikrotik", "ubiquiti", "cisco", "cambium", "huawei", "generic"
    vendor_slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Nama tampilan
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Rate-limit attribute utama ---
    # Nama atribut RADIUS (misal: "Mikrotik-Rate-Limit", "WISPr-Bandwidth-Max-Down")
    # NULL jika format = NONE
    rate_limit_attribute: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Format penghitungan nilai atribut
    rate_limit_format: Mapped[RateLimitFormat] = mapped_column(
        Enum(RateLimitFormat, name="rate_limit_format_enum"),
        nullable=False,
        default=RateLimitFormat.NONE,
    )

    # --- Atribut tambahan ---
    # JSON array dari objek {attribute, op, format} untuk vendor yang butuh
    # lebih dari satu atribut bandwidth (contoh: Ubiquiti butuh Max-Down + Max-Up)
    # Contoh value:
    # [{"attribute": "WISPr-Bandwidth-Max-Up", "op": "=", "format": "bps_single_up"}]
    extra_group_reply_attrs: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Profil bawaan tidak bisa dihapus lewat API
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Backref dari nas_ext
    nas_list: Mapped[list["NasExt"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "NasExt", back_populates="vendor_profile"
    )

    def __repr__(self) -> str:
        return f"<NasVendorProfile id={self.id} slug={self.vendor_slug!r} format={self.rate_limit_format}>"
