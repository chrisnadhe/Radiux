"""Service layer untuk penjadwalan task otomatis (Background Jobs)."""

import logging
from datetime import UTC, date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.customers import Customer, CustomerStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.radius_core import RadAcct
from app.services.coa_service import kick_user

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def auto_suspend_job() -> None:
    """Task yang mengecek dan melakukan auto-suspend pada pelanggan yang expired atau menunggak."""
    logger.info("Memulai eksekusi Auto-Suspend Job...")

    now_utc = datetime.now(UTC)
    today = date.today()

    async with AsyncSessionLocal() as db:
        # 1. Cek Pelanggan Prabayar (Voucher/Hotspot) yang Expired
        stmt_expired = select(Customer).where(Customer.status == CustomerStatus.ACTIVE, Customer.expires_at < now_utc)
        expired_customers = (await db.scalars(stmt_expired)).all()

        for cust in expired_customers:
            cust.status = CustomerStatus.SUSPENDED
            logger.info(f"Auto-suspend pelanggan {cust.radius_username} karena expired.")
            await kick_active_session(db, cust.radius_username)

        # 2. Cek Pelanggan Pascabayar dengan Invoice Unpaid yang melewati Due Date
        stmt_unpaid = select(Invoice).where(Invoice.status == InvoiceStatus.UNPAID, Invoice.due_date < today)
        unpaid_invoices = (await db.scalars(stmt_unpaid)).all()

        for inv in unpaid_invoices:
            # Ambil customernya
            cust = await db.scalar(select(Customer).where(Customer.id == inv.customer_id))
            if cust and cust.status == CustomerStatus.ACTIVE:
                cust.status = CustomerStatus.SUSPENDED
                logger.info(
                    f"Auto-suspend pelanggan {cust.radius_username} karena menunggak tagihan {inv.invoice_number}."
                )
                await kick_active_session(db, cust.radius_username)

        await db.commit()
    logger.info("Auto-Suspend Job selesai.")


async def kick_active_session(db: AsyncSession, username: str) -> None:
    """Mencari sesi aktif dari username tersebut dan memutusnya menggunakan CoA/Disconnect."""
    # Cari sesi aktif di radacct
    active_sessions = await db.scalars(
        select(RadAcct).where(RadAcct.username == username, RadAcct.acctstoptime.is_(None))
    )
    for session in active_sessions.all():
        await kick_user(db, session.radacctid)


def start_scheduler() -> None:
    """Memulai scheduler. Dipanggil di lifespan FastAPI."""
    if not scheduler.running:
        # Tambahkan job, misal berjalan setiap 1 jam
        scheduler.add_job(auto_suspend_job, "interval", hours=1, id="auto_suspend_job", replace_existing=True)
        scheduler.start()
        logger.info("APScheduler berhasil dijalankan.")


def stop_scheduler() -> None:
    """Menghentikan scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler dihentikan.")
