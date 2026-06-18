"""Router untuk operasi manajemen Tenants (Hanya Superadmin)."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.tenants import Tenant, TenantStatus
from app.services import wallet_service

router = APIRouter(prefix="/tenants", tags=["Tenants"])

class TenantCreate(BaseModel):
    name: str
    slug: str
    notes: str | None = None

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    balance: float
    is_active: bool
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)

class TenantTopup(BaseModel):
    amount: float
    notes: str | None = None

@router.get("/", response_model=list[TenantResponse])
async def list_tenants(
    user: CurrentUser, 
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List semua tenant."""
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
    result = await db.scalars(select(Tenant).where(Tenant.id != 1).order_by(Tenant.id.desc()))
    return result.all()

@router.post("/", response_model=TenantResponse)
async def create_tenant(
    req: TenantCreate,
    user: CurrentUser, 
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Create tenant baru."""
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
    
    tenant = Tenant(
        name=req.name,
        slug=req.slug,
        notes=req.notes
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.post("/{tenant_id}/topup", response_model=dict[str, Any])
async def topup_tenant(
    tenant_id: int,
    req: TenantTopup,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Top up saldo reseller."""
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
        
    trx = await wallet_service.add_balance(
        db=db,
        tenant_id=tenant_id,
        amount=req.amount,
        notes=req.notes or f"Top up oleh {user.username}"
    )
    await db.commit()
    return {"status": "success", "new_balance": float(trx.balance_after)}

@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Suspend reseller."""
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
        
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant tidak ditemukan")
        
    tenant.status = TenantStatus.SUSPENDED
    tenant.is_active = False
    await db.commit()
    return {"status": "success"}

@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Activate reseller."""
    if not user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
        
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant tidak ditemukan")
        
    tenant.status = TenantStatus.ACTIVE
    tenant.is_active = True
    await db.commit()
    return {"status": "success"}
