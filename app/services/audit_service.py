"""Audit service — Mencatat jejak aktivitas ke dalam database (Phase 9)."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    user_id: int | None = None,
    table_name: str | None = None,
    record_id: str | int | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Catat aktivitas krusial ke tabel audit_logs.

    Args:
        db: DB session.
        action: Nama aksi (contoh: 'LOGIN', 'CREATE_CUSTOMER').
        user_id: ID admin_users yang melakukan aksi (opsional).
        table_name: Nama tabel yang terpengaruh (opsional).
        record_id: ID record yang terpengaruh (opsional).
        details: Payload JSON terkait detail aksi (opsional).
        ip_address: IP address pengguna (opsional).

    Returns:
        Instance AuditLog yang baru dibuat.
    """
    if details is None:
        details = {}

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=str(record_id) if record_id else None,
        details=details,
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    return audit_log
