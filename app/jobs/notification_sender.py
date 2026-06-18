"""Job terjadwal untuk mengirim notifikasi peringatan (Phase 8)."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.customers import Customer, CustomerStatus
from app.models.notifications import NotificationEventType
from app.models.tenants import Tenant
from app.services.notification_service import send_notification

logger = logging.getLogger(__name__)


async def check_expiry_and_notify() -> None:
    """Cek customer prabayar yang mendekati expired (H-3 dan H-1)."""
    logger.info("Memulai job: Cek Expiry & Kirim Notifikasi...")
    now_utc = datetime.now(UTC)

    # Range untuk H-1 (24 jam ke depan)
    h1_start = now_utc + timedelta(days=1)
    h1_end = h1_start + timedelta(hours=1)  # toleransi 1 jam

    # Range untuk H-3 (72 jam ke depan)
    h3_start = now_utc + timedelta(days=3)
    h3_end = h3_start + timedelta(hours=1)

    async with AsyncSessionLocal() as db:
        # Cek H-1
        stmt_h1 = select(Customer).where(
            Customer.status == CustomerStatus.ACTIVE,
            Customer.expires_at >= h1_start,
            Customer.expires_at < h1_end,
        )
        h1_customers = (await db.scalars(stmt_h1)).all()
        for cust in h1_customers:
            logger.info(f"Mengirim notifikasi H-1 ke {cust.radius_username}")
            msg = f"Pelanggan <b>{cust.full_name}</b> ({cust.radius_username}) akan expired dalam 1 hari."
            await send_notification(
                db,
                recipient_type="customer",
                recipient_id=cust.id,
                event_type=NotificationEventType.EXPIRY_WARNING,
                title="Peringatan: Masa Aktif Berakhir Besok",
                message=msg,
                tenant_id=cust.tenant_id,
            )

        # Cek H-3
        stmt_h3 = select(Customer).where(
            Customer.status == CustomerStatus.ACTIVE,
            Customer.expires_at >= h3_start,
            Customer.expires_at < h3_end,
        )
        h3_customers = (await db.scalars(stmt_h3)).all()
        for cust in h3_customers:
            logger.info(f"Mengirim notifikasi H-3 ke {cust.radius_username}")
            msg = f"Pelanggan <b>{cust.full_name}</b> ({cust.radius_username}) akan expired dalam 3 hari."
            await send_notification(
                db,
                recipient_type="customer",
                recipient_id=cust.id,
                event_type=NotificationEventType.EXPIRY_WARNING,
                title="Peringatan: Masa Aktif Berakhir (H-3)",
                message=msg,
                tenant_id=cust.tenant_id,
            )

    logger.info("Job Cek Expiry selesai.")


async def check_low_balance_and_notify() -> None:
    """Cek saldo tiap reseller, jika di bawah threshold, kirim notifikasi."""
    logger.info("Memulai job: Cek Saldo Reseller (Low Balance)...")
    settings = get_settings()
    threshold = settings.notification_low_balance_threshold

    async with AsyncSessionLocal() as db:
        # Loop ke semua tenant reseller
        tenants = (await db.scalars(select(Tenant))).all()
        for tenant in tenants:
            balance = float(tenant.balance)
            if balance < threshold:
                logger.info(f"Saldo {tenant.name} menipis: Rp {balance}")
                msg = (
                    f"Saldo untuk reseller <b>{tenant.name}</b> saat ini Rp {balance:,.0f}. "
                    f"Sudah di bawah batas aman (Rp {threshold:,.0f}). Harap segera Top-Up."
                )
                await send_notification(
                    db,
                    recipient_type="tenant",
                    recipient_id=tenant.id,
                    event_type=NotificationEventType.LOW_BALANCE,
                    title="Peringatan: Saldo Reseller Menipis",
                    message=msg,
                    tenant_id=tenant.id,
                )

    logger.info("Job Cek Saldo selesai.")
