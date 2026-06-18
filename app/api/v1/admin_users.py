"""Router untuk operasi manajemen Admin Users."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.security import get_password_hash
from app.models.admin_users import AdminUser, AdminRole

router = APIRouter(prefix="/admin-users", tags=["Admin Users"])

class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    role: AdminRole
    tenant_id: int | None = None
    
    @field_validator("tenant_id", "full_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

class AdminUserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    full_name: str | None = None
    role: AdminRole | None = None
    tenant_id: int | None = None
    is_active: bool | None = None
    
    @field_validator("tenant_id", "full_name", "password", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

class TenantResponse(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    tenant_id: int | None
    tenant: TenantResponse | None = None
    model_config = ConfigDict(from_attributes=True)

@router.get("/", response_model=list[AdminUserResponse])
async def list_admin_users(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """List semua admin user (Superadmin can see all, Reseller can see their own tenant's users)."""
    stmt = select(AdminUser).options(joinedload(AdminUser.tenant)).order_by(AdminUser.id.desc())
    if not user.is_superadmin:
        stmt = stmt.where(AdminUser.tenant_id == user.tenant_id)
        
    result = await db.scalars(stmt)
    return result.all()

@router.post("/", response_model=AdminUserResponse)
async def create_admin_user(
    req: AdminUserCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Buat admin user baru."""
    # Hanya superadmin yang bisa membuat user lintas tenant. Reseller hanya bisa membuat operator/viewer untuk tenantnya.
    if not user.is_superadmin:
        if req.tenant_id != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tidak bisa membuat user untuk tenant lain")
        if req.role in [AdminRole.SUPERADMIN, AdminRole.RESELLER]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya Superadmin yang bisa membuat role ini")
            
    # Cek username
    existing = await db.scalar(select(AdminUser).where(AdminUser.username == req.username))
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username sudah dipakai")
        
    hashed_password = get_password_hash(req.password)
    
    new_user = AdminUser(
        username=req.username,
        email=req.email,
        hashed_password=hashed_password,
        full_name=req.full_name,
        role=req.role,
        tenant_id=req.tenant_id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Reload with tenant info
    return await db.scalar(select(AdminUser).options(joinedload(AdminUser.tenant)).where(AdminUser.id == new_user.id))

@router.put("/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    user_id: int,
    req: AdminUserUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update admin user."""
    target_user = await db.scalar(select(AdminUser).options(joinedload(AdminUser.tenant)).where(AdminUser.id == user_id))
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")
        
    if not user.is_superadmin:
        if target_user.tenant_id != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
        if req.role and req.role in [AdminRole.SUPERADMIN, AdminRole.RESELLER]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tidak dapat meng-assign role ini")
        if req.tenant_id is not None and req.tenant_id != user.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tidak dapat memindahkan tenant")
            
    if req.email is not None:
        target_user.email = req.email
    if req.full_name is not None:
        target_user.full_name = req.full_name
    if req.role is not None:
        target_user.role = req.role
    if req.tenant_id is not None:
        target_user.tenant_id = req.tenant_id
    if req.is_active is not None:
        target_user.is_active = req.is_active
    if req.password:
        target_user.hashed_password = get_password_hash(req.password)
        
    await db.commit()
    await db.refresh(target_user)
    return target_user
