"""Router Monitoring — Endpoint REST dan SSE untuk sesi aktif dan NAS status."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import CurrentUser, DbSession
from app.models.admin_users import AdminUser
from app.schemas.monitoring import ActiveSessionRead, NasStatusRead
from app.services import monitoring_service

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def _get_tenant_id(user: "AdminUser") -> int | None:
    return None if user.is_superadmin else user.tenant_id


@router.get("/sessions", response_model=list[ActiveSessionRead], summary="List Sesi Aktif")
async def get_sessions(
    db: DbSession,
    user: CurrentUser,
) -> list[ActiveSessionRead]:
    """Mengembalikan daftar sesi aktif secara satu-waktu (REST)."""
    scope_tenant_id = _get_tenant_id(user)
    return await monitoring_service.get_active_sessions(db, tenant_id=scope_tenant_id)


@router.get("/nas-status", response_model=list[NasStatusRead], summary="Status NAS")
async def get_nas_status(
    db: DbSession,
    user: CurrentUser,
) -> list[NasStatusRead]:
    """Mengembalikan status online/offline untuk tiap NAS."""
    scope_tenant_id = _get_tenant_id(user)
    return await monitoring_service.get_nas_status(db, tenant_id=scope_tenant_id)


@router.get("/stream", summary="SSE Stream Sesi Aktif")
async def stream_sessions(
    user: CurrentUser,
) -> EventSourceResponse:
    """Endpoint Server-Sent Events (SSE) untuk update sesi realtime."""
    scope_tenant_id = _get_tenant_id(user)
    return EventSourceResponse(monitoring_service.stream_active_sessions(tenant_id=scope_tenant_id))
