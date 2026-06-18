"""Model AdminUser — akun login panel Radiux (superadmin/reseller/operator/viewer)."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AdminRole(enum.StrEnum):
    """Role hierarki dalam Radiux.

    - SUPERADMIN: akses penuh ke semua tenant
    - RESELLER: akses hanya ke data tenant sendiri
    - OPERATOR: bisa CRUD customer tapi tidak bisa ubah billing/NAS
    - VIEWER: read-only di semua halaman tenant sendiri
    """

    SUPERADMIN = "superadmin"
    RESELLER = "reseller"
    OPERATOR = "operator"
    VIEWER = "viewer"


class AdminUser(Base):
    """Akun admin/reseller/operator yang bisa login ke panel Radiux."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name="admin_role_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=AdminRole.OPERATOR,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # NULL berarti superadmin (tidak terikat tenant manapun)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    tenant: Mapped["Tenant | None"] = relationship("Tenant", foreign_keys=[tenant_id])  # type: ignore[name-defined]  # noqa: F821

    @property
    def is_superadmin(self) -> bool:
        """Return True jika user adalah superadmin."""
        return self.role == AdminRole.SUPERADMIN

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} username={self.username!r} role={self.role}>"
