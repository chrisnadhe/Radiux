"""Monitoring Service — logika untuk accounting dan live session."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.customers import Customer
from app.models.nas_ext import NasExt
from app.models.radius_core import NasCore, RadAcct
from app.schemas.monitoring import ActiveSessionRead, NasStatusRead


async def get_active_sessions(db: AsyncSession, tenant_id: int | None = None) -> list[ActiveSessionRead]:
    """Mengambil semua sesi aktif (acctstoptime IS NULL)."""
    # Join dengan Customer untuk ambil full_name
    query = (
        select(RadAcct, Customer.full_name)
        .outerjoin(Customer, RadAcct.username == Customer.radius_username)
        .where(RadAcct.acctstoptime.is_(None))
    )

    if tenant_id is not None:
        query = query.where(Customer.tenant_id == tenant_id)

    result = await db.execute(query.order_by(RadAcct.acctstarttime.desc()))

    sessions = []
    for row in result:
        radacct, full_name = row
        session_data = ActiveSessionRead.model_validate(radacct)
        session_data.full_name = full_name
        sessions.append(session_data)

    return sessions


async def get_nas_status(db: AsyncSession, tenant_id: int | None = None) -> list[NasStatusRead]:
    """Mengembalikan status tiap NAS (online jika ada update/sesi aktif baru-baru ini)."""

    # Toleransi offline: 10 menit tanpa data radacct baru
    threshold = datetime.now(UTC) - timedelta(minutes=10)

    query = select(NasCore, NasExt).join(NasExt, NasCore.nasname == NasExt.nasname)
    if tenant_id is not None:
        query = query.where(NasExt.tenant_id == tenant_id)

    nas_result = await db.execute(query)
    nas_pairs = list(nas_result.all())

    statuses = []
    for core, ext in nas_pairs:
        # Cari acctupdatetime atau acctstarttime terbaru untuk NAS ini
        latest_acct = await db.execute(
            select(func.max(func.coalesce(RadAcct.acctupdatetime, RadAcct.acctstarttime))).where(
                RadAcct.nasipaddress == core.nasname
            )
        )
        last_update = latest_acct.scalar_one_or_none()

        # Jika last_update timezone-naive (misal PostgreSQL without timezone issue), buat jadi aware
        if last_update and last_update.tzinfo is None:
            last_update = last_update.replace(tzinfo=UTC)

        # Hitung session aktif untuk NAS ini
        active_count_res = await db.execute(
            select(func.count(RadAcct.radacctid))
            .where(RadAcct.nasipaddress == core.nasname)
            .where(RadAcct.acctstoptime.is_(None))
        )
        active_count = active_count_res.scalar_one()

        is_online = False
        if last_update is not None and last_update >= threshold:
            is_online = True

        statuses.append(
            NasStatusRead(
                nasname=core.nasname,
                shortname=core.shortname,
                is_online=is_online,
                last_update=last_update,
                active_sessions=active_count,
            )
        )

    return statuses


async def stream_active_sessions(tenant_id: int | None = None):
    """Async generator untuk SSE yang mengirim data sesi secara periodik."""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                sessions = await get_active_sessions(db, tenant_id)
                session_data = [s.model_dump(by_alias=True, mode="json") for s in sessions]

                yield {"event": "session_update", "data": json.dumps(session_data)}

                statuses = await get_nas_status(db, tenant_id)
                nas_data = [s.model_dump(mode="json") for s in statuses]

                yield {"event": "nas_update", "data": json.dumps(nas_data)}
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"SSE Error: {e}")

        await asyncio.sleep(5)  # Polling setiap 5 detik
