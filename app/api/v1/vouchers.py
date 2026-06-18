"""API Endpoints untuk manajemen Voucher Prabayar."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import voucher_service

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])

class VoucherGenerateRequest(BaseModel):
    name: str = Field(..., max_length=128)
    quantity: int = Field(..., gt=0, le=1000)
    package_id: int
    tenant_id: int = 1  # Untuk sementara default 1 (Main ISP)
    length: int = Field(6, ge=4, le=16)
    prefix: str = Field("", max_length=16)
    notes: str | None = None

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_vouchers(
    req: VoucherGenerateRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Generate batch voucher prabayar baru."""
    try:
        batch = await voucher_service.create_voucher_batch(
            db=db,
            name=req.name,
            qty=req.quantity,
            package_id=req.package_id,
            tenant_id=req.tenant_id,
            length=req.length,
            prefix=req.prefix,
            notes=req.notes
        )
        return {"status": "success", "batch_id": batch.id, "quantity": batch.quantity}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/batches")
async def list_voucher_batches(
    tenant_id: int = 1,
    db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Mendapatkan daftar batch voucher."""
    batches = await voucher_service.get_voucher_batches(db, tenant_id)
    return [
        {
            "id": b.id,
            "name": b.name,
            "quantity": b.quantity,
            "package_id": b.package_id,
            "created_at": b.created_at
        }
        for b in batches
    ]

@router.get("/batches/{batch_id}/print")
async def print_vouchers(
    batch_id: int,
    tenant_id: int = 1,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Mendapatkan detail voucher untuk di-print (UI akan menggunakan HTML)."""
    vouchers = await voucher_service.get_vouchers_by_batch(db, batch_id, tenant_id)
    if not vouchers:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan atau kosong")
        
    return {
        "batch_id": batch_id,
        "vouchers": [
            {
                "username": v.radius_username,
                "password": v.voucher_password,
                "package_id": v.package_id
            } for v in vouchers
        ]
    }
