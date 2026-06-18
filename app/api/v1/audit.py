"""Router Audit Logs — Melihat jejak aktivitas (Phase 9)."""

import math

from fastapi import APIRouter, Query
from sqlalchemy import desc, select

from app.core.dependencies import DbSession, SuperAdminUser
from app.models.audit_logs import AuditLog
from app.schemas.audit import AuditLogListResponse, AuditLogRead

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=AuditLogListResponse, summary="List Audit Logs")
async def list_audit_logs(
    db: DbSession,
    user: SuperAdminUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
) -> AuditLogListResponse:
    """List audit logs dengan pagination (Hanya Superadmin)."""
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)

    # Hitung total
    from sqlalchemy import func
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Ambil data
    stmt = stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    logs = (await db.scalars(stmt)).all()

    pages = math.ceil(total / page_size) if total else 0
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
