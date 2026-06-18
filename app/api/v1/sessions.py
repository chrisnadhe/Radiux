"""Router untuk operasi manajemen sesi (termasuk Kick)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.services import coa_service

router = APIRouter(prefix="/sessions", tags=["Sessions"])

def _get_tenant_id(user: "AdminUser") -> int | None:
    return None if user.is_superadmin else user.tenant_id


@router.post("/{radacctid}/kick", summary="Memutus sesi (Kick User)")
async def kick_session(radacctid: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Mengirim Disconnect-Request ke NAS terkait sesi ini."""
    scope_tenant_id = _get_tenant_id(user)
    try:
        success = await coa_service.kick_user(db, radacctid, scope_tenant_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    if not success:
        # Kita tetap mereturn 200 dengan status info,
        # karena di level DB kita paksakan close, hanya pengiriman UDP yang gagal
        return {
            "status": "warning",
            "message": "NAS gagal merespons atau Timeout, namun sesi telah dibersihkan dari database.",
        }

    return {"status": "success", "message": "User berhasil diputus."}
