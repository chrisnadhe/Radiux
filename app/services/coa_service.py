"""Service layer untuk operasi RADIUS CoA dan Disconnect."""

import logging
from datetime import UTC, datetime

from pyrad.client import Timeout
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customers import Customer
from app.models.nas_ext import NasExt
from app.models.radius_core import NasCore, RadAcct
from app.radius.client import create_client
from app.radius.packet_builder import build_disconnect_request

logger = logging.getLogger(__name__)


async def kick_user(db: AsyncSession, radacctid: int, tenant_id: int | None = None) -> bool:
    """Memutus sesi pengguna secara paksa.

    1. Cari RadAcct berdasarkan ID.
    2. Cari NAS bersangkutan untuk mendapatkan IP dan Secret.
    3. Kirim paket Disconnect-Request ke NAS lewat pyrad.
    4. Jika NAS merespons dengan Disconnect-ACK, set acctstoptime.
    5. Jika gagal/Timeout, perlakuan saat ini adalah set stoptime juga
       sebagai fallback (agar dianggap offline di sistem), kecuali ditentukan lain.
    """
    # 1. Cari sesi aktif
    acct = await db.scalar(select(RadAcct).where(RadAcct.radacctid == radacctid))
    if not acct:
        logger.error(f"Sesi dengan id {radacctid} tidak ditemukan.")
        return False

    if tenant_id is not None:
        customer = await db.scalar(select(Customer).where(Customer.radius_username == acct.username))
        if customer and customer.tenant_id != tenant_id:
            raise PermissionError("Sesi ini bukan milik tenant Anda")

    if acct.acctstoptime is not None:
        logger.info(f"Sesi {radacctid} sudah berstatus terputus.")
        return True

    # 2. Dapatkan IP NAS dan Secret
    nas_ip = acct.nasipaddress
    if not nas_ip:
        logger.error("NAS IP tidak tersedia pada sesi ini.")
        return False

    nas_core = await db.scalar(select(NasCore).where(NasCore.nasname == nas_ip))
    if not nas_core:
        logger.error(f"Data NAS {nas_ip} tidak ditemukan di nas_core.")
        return False

    nas_ext = await db.scalar(select(NasExt).where(NasExt.nasname == nas_ip))
    coa_port = nas_ext.coa_port if nas_ext and nas_ext.coa_port else 3799

    # 3. Setup client dan paket
    try:
        client = create_client(nas_ip=nas_ip, secret=nas_core.secret, coa_port=coa_port)
        req = build_disconnect_request(
            client=client, username=acct.username, session_id=acct.acctsessionid, framed_ip=acct.framedipaddress
        )

        # Kirim secara sinkron lewat SendPacket (pyrad berbasis blok IO pada socket UDP).
        # Walau blocking, karena hanya UDP dengan timeout sangat singkat,
        # kita biarkan ini berjalan di thread executor asyncio jika nanti butuh dioptimasi.
        logger.info(f"Mengirim Disconnect-Request ke {nas_ip} untuk user {acct.username}")
        reply = client.SendPacket(req)

        if reply.code == 41:  # Disconnect-ACK
            logger.info(f"Disconnect sukses (ACK) dari NAS {nas_ip}.")
            success = True
        else:
            logger.warning(f"NAS {nas_ip} merespons dengan NAK (code: {reply.code}).")
            success = False

    except Timeout:
        logger.error(f"Timeout saat menghubungi NAS {nas_ip} untuk kick user {acct.username}.")
        success = False
    except Exception as e:
        logger.exception(f"Error tidak terduga saat kick user: {e}")
        success = False

    # 4. Fallback Force-Close Session di DB jika Timeout / gagal namun kita ingin paksakan bersih
    # Sesuai kesepakatan Open Question: Kita akan paksa close session di DB agar tidak menyangkut.
    # Jika Anda ingin mengubah ini, kita bisa kondisikan if success:
    acct.acctstoptime = datetime.now(UTC)
    acct.acctterminatecause = "Admin-Reset"
    await db.commit()

    return success
