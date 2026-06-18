"""Model AuditLog — Merekam jejak aktivitas sistem (Phase 9)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuditLog(Base):
    """Log audit untuk merekam aksi krusial (Security & Audit)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Siapa yang melakukan aksi
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Aksi yang dilakukan (contoh: LOGIN, CREATE_CUSTOMER, UPDATE_NAS)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Entitas apa yang dimodifikasi
    table_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    record_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Detail perubahan atau informasi tambahan
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Dari IP mana aksi ini dilakukan
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Kapan aksi ini terjadi
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    user: Mapped["AdminUser | None"] = relationship("AdminUser")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        Index("ix_audit_logs_action_created_at", action, created_at.desc()),
        Index("ix_audit_logs_user_id_created_at", user_id, created_at.desc()),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} user_id={self.user_id} "
            f"action={self.action} record={self.table_name}:{self.record_id}>"
        )
