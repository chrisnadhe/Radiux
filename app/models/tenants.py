"""Model Tenant — reseller/tenant dalam hierarki multi-tenant Radiux."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TenantStatus(enum.StrEnum):
    """Status aktif/non-aktif tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class Tenant(Base):
    """Reseller / tenant dalam sistem Radiux.

    Superadmin dapat membuat tenant; setiap tenant mengelola customer-nya
    sendiri secara terisolasi (semua data customer wajib ber-scope tenant_id).
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TenantStatus.ACTIVE,
    )
    # Saldo reseller (dalam satuan currency lokal, contoh: Rupiah)
    balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships (akan diisi saat model lain dibuat)
    # admin_users: list["AdminUser"] = relationship(back_populates="tenant")
    # customers: list["Customer"] = relationship(back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r} status={self.status}>"
