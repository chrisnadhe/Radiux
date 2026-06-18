"""API Endpoints untuk manajemen Voucher Prabayar."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.admin_users import AdminUser
from app.services import voucher_service, wallet_service

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


def _get_tenant_id(user: "AdminUser") -> int | None:
    return None if user.is_superadmin else user.tenant_id


class VoucherGenerateRequest(BaseModel):
    name: str = Field(..., max_length=128)
    quantity: int = Field(..., gt=0, le=1000)
    package_id: int
    tenant_id: int | None = None  # Akan di-override jika reseller
    length: int = Field(6, ge=4, le=16)
    prefix: str = Field("", max_length=16)
    notes: str | None = None


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_vouchers(
    req: VoucherGenerateRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Generate batch voucher prabayar baru."""
    # Enforce tenant_id
    if not user.is_superadmin:
        req.tenant_id = user.tenant_id
    elif not req.tenant_id:
        raise HTTPException(status_code=400, detail="Superadmin harus menyertakan tenant_id")

    try:
        batch = await voucher_service.create_voucher_batch(
            db=db,
            name=req.name,
            qty=req.quantity,
            package_id=req.package_id,
            tenant_id=req.tenant_id,
            length=req.length,
            prefix=req.prefix,
            notes=req.notes,
        )
        return {"status": "success", "batch_id": batch.id, "quantity": batch.quantity}
    except wallet_service.InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches")
async def list_voucher_batches(
    user: CurrentUser, tenant_id: int | None = None, db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Mendapatkan daftar batch voucher."""
    scope_tenant_id = _get_tenant_id(user) or tenant_id
    if not scope_tenant_id and not user.is_superadmin:
        scope_tenant_id = user.tenant_id

    batches = await voucher_service.get_voucher_batches(db, scope_tenant_id)
    return [
        {"id": b.id, "name": b.name, "quantity": b.quantity, "package_id": b.package_id, "created_at": b.created_at}
        for b in batches
    ]


@router.get("/batches/{batch_id}/print")
async def print_vouchers(batch_id: int, user: CurrentUser, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Mendapatkan detail voucher untuk di-print (UI akan menggunakan HTML)."""
    scope_tenant_id = _get_tenant_id(user)
    vouchers = await voucher_service.get_vouchers_by_batch(db, batch_id, scope_tenant_id)
    if not vouchers:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan atau kosong")

    return {
        "batch_id": batch_id,
        "vouchers": [
            {"username": v.radius_username, "password": v.voucher_password, "package_id": v.package_id}
            for v in vouchers
        ],
    }
