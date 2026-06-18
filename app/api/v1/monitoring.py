"""Router Monitoring — Endpoint REST dan SSE untuk sesi aktif dan NAS status."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import CurrentUserId, DbSession
from app.schemas.monitoring import ActiveSessionRead, NasStatusRead
from app.services import monitoring_service

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/sessions", response_model=list[ActiveSessionRead], summary="List Sesi Aktif")
async def get_sessions(
    db: DbSession,
    user_id: CurrentUserId,
) -> list[ActiveSessionRead]:
    """Mengembalikan daftar sesi aktif secara satu-waktu (REST)."""
    # TODO: Jika user_id adalah tenant/reseller, pass tenant_id
    return await monitoring_service.get_active_sessions(db)


@router.get("/nas-status", response_model=list[NasStatusRead], summary="Status NAS")
async def get_nas_status(
    db: DbSession,
    user_id: CurrentUserId,
) -> list[NasStatusRead]:
    """Mengembalikan status online/offline untuk tiap NAS."""
    return await monitoring_service.get_nas_status(db)


@router.get("/stream", summary="SSE Stream Sesi Aktif")
async def stream_sessions(
    user_id: CurrentUserId,
) -> EventSourceResponse:
    """Endpoint Server-Sent Events (SSE) untuk update sesi realtime."""
    # Timeout opsional bisa disetel untuk mencegah koneksi gantung terlalu lama
    return EventSourceResponse(monitoring_service.stream_active_sessions())
