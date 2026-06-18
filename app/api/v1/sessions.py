"""Router untuk operasi manajemen sesi (termasuk Kick)."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import coa_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/{radacctid}/kick", summary="Memutus sesi (Kick User)")
async def kick_session(radacctid: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Mengirim Disconnect-Request ke NAS terkait sesi ini."""
    success = await coa_service.kick_user(db, radacctid)
    if not success:
        # Kita tetap mereturn 200 dengan status info,
        # karena di level DB kita paksakan close, hanya pengiriman UDP yang gagal
        return {
            "status": "warning",
            "message": "NAS gagal merespons atau Timeout, namun sesi telah dibersihkan dari database.",
        }

    return {"status": "success", "message": "User berhasil diputus."}
