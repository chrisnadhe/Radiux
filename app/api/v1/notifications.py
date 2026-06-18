"""API Endpoints untuk manajemen Notifikasi."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.notifications import Notification, NotificationChannel, NotificationEventType
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: int
    recipient_type: str
    recipient_id: int | None
    channel: str
    event_type: str
    title: str
    message: str
    status: str
    error_message: str | None
    tenant_id: int | None
    sent_at: str | None = None
    created_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TestNotificationRequest(BaseModel):
    channel: NotificationChannel = NotificationChannel.TELEGRAM
    title: str = "Test Notifikasi"
    message: str = "Ini adalah pesan percobaan dari sistem Radiux."


@router.get("/", response_model=list[NotificationResponse])
async def list_notifications(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Sequence[Notification]:
    """Ambil riwayat notifikasi (di-scope ke tenant untuk reseller)."""
    tenant_id = None if current_user.is_superadmin else current_user.tenant_id
    notifs = await notification_service.get_notifications(db, tenant_id=tenant_id, limit=limit, offset=offset)
    return notifs


@router.post("/test", response_model=NotificationResponse)
async def send_test_notification(
    req: TestNotificationRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Notification:
    """Kirim notifikasi testing (berguna untuk validasi setup Telegram/Email)."""

    # Untuk test, anggap saja penerimanya admin itu sendiri
    tenant_id = None if current_user.is_superadmin else current_user.tenant_id

    notif = await notification_service.send_notification(
        db=db,
        recipient_type="admin",
        recipient_id=current_user.id,
        event_type=NotificationEventType.TEST,
        title=req.title,
        message=req.message,
        tenant_id=tenant_id,
        force_channel=req.channel,
    )

    return notif
