"""Service untuk mengelola dan mengirim Notifikasi (Phase 8)."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.notifications import Notification, NotificationChannel, NotificationEventType, NotificationStatus

logger = logging.getLogger(__name__)


async def _send_via_telegram(bot_token: str, chat_id: str, message: str) -> tuple[bool, str | None]:
    """Mengirim pesan via Telegram Bot API."""
    if not bot_token or not chat_id:
        return False, "Telegram config incomplete"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return True, None
    except httpx.HTTPError as e:
        err_msg = f"HTTP Error: {str(e)}"
        logger.error(f"Gagal kirim Telegram: {err_msg}")
        return False, err_msg
    except Exception as e:
        err_msg = f"Unknown Error: {str(e)}"
        logger.error(f"Gagal kirim Telegram: {err_msg}")
        return False, err_msg


async def send_notification(
    db: AsyncSession,
    recipient_type: str,
    recipient_id: int | None,
    event_type: NotificationEventType,
    title: str,
    message: str,
    tenant_id: int | None = None,
    force_channel: NotificationChannel | None = None,
) -> Notification:
    """Fungsi utama untuk membuat dan mengirim notifikasi.

    Jika `force_channel` tidak diatur, defaultnya akan mencoba mengirim via Telegram.
    (Bisa diperluas nanti untuk cek preferensi pelanggan).
    """
    channel = force_channel or NotificationChannel.TELEGRAM
    settings = get_settings()

    # Buat record di DB (Status PENDING)
    notif = Notification(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        channel=channel,
        event_type=event_type,
        title=title,
        message=message,
        status=NotificationStatus.PENDING,
        tenant_id=tenant_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)

    success = False
    error_msg = None

    # Eksekusi pengiriman sesuai channel
    if channel == NotificationChannel.TELEGRAM:
        token = settings.telegram_bot_token
        chat_id = settings.telegram_admin_chat_id  # Fallback

        if recipient_type == "customer" and recipient_id:
            from app.models.customers import Customer
            cust = await db.scalar(select(Customer).where(Customer.id == recipient_id))
            if cust and cust.telegram_chat_id:
                chat_id = cust.telegram_chat_id
        elif recipient_type == "tenant" and recipient_id:
            from app.models.tenants import Tenant
            tenant_obj = await db.scalar(select(Tenant).where(Tenant.id == recipient_id))
            if tenant_obj and tenant_obj.telegram_chat_id:
                chat_id = tenant_obj.telegram_chat_id

        if not token or not chat_id:
            notif.status = NotificationStatus.SKIPPED
            notif.error_message = "Telegram not configured"
            await db.commit()
            return notif

        # Tambahkan prefix judul ke pesan
        full_message = f"<b>{title}</b>\n\n{message}"
        success, error_msg = await _send_via_telegram(token, chat_id, full_message)

    elif channel == NotificationChannel.EMAIL:
        notif.status = NotificationStatus.SKIPPED
        notif.error_message = "Email channel not fully implemented yet"
        await db.commit()
        return notif

    elif channel == NotificationChannel.WHATSAPP:
        notif.status = NotificationStatus.SKIPPED
        notif.error_message = "WhatsApp channel not implemented yet"
        await db.commit()
        return notif

    # Update status record
    if success:
        notif.status = NotificationStatus.SENT
        notif.sent_at = datetime.now(UTC)
    else:
        notif.status = NotificationStatus.FAILED
        notif.error_message = error_msg

    await db.commit()
    await db.refresh(notif)
    return notif


async def get_notifications(
    db: AsyncSession,
    tenant_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Notification]:
    """Ambil riwayat notifikasi (di-scope by tenant_id jika reseller)."""
    stmt = select(Notification).order_by(desc(Notification.created_at))
    if tenant_id is not None:
        stmt = stmt.where(Notification.tenant_id == tenant_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.scalars(stmt)
    return result.all()
