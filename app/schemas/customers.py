"""Pydantic schemas untuk Customer CRUD."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.customers import CustomerStatus


class CustomerBase(BaseModel):
    """Field yang dipakai di Create dan Update."""

    full_name: str = Field(..., min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=32)
    address: str | None = None
    notes: str | None = None


class CustomerCreate(CustomerBase):
    """Payload untuk membuat customer baru + provisioning RADIUS."""

    radius_username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9._@-]+$",
        description="Username RADIUS — harus unik di seluruh sistem",
    )
    radius_password: str = Field(
        ...,
        min_length=6,
        max_length=64,
        description="Password RADIUS (plain, akan di-hash)",
    )
    package_id: int | None = None
    tenant_id: int = Field(..., description="Tenant/reseller yang memiliki customer ini")


class CustomerUpdate(CustomerBase):
    """Payload untuk update customer — semua field opsional."""

    full_name: str | None = Field(None, min_length=1, max_length=128)
    package_id: int | None = None
    status: CustomerStatus | None = None
    # Password RADIUS bisa diubah; None = tidak berubah
    radius_password: str | None = Field(None, min_length=6, max_length=64)


class CustomerRead(CustomerBase):
    """Response schema Customer — untuk API dan tampilan."""

    id: int
    radius_username: str
    status: CustomerStatus
    is_active: bool
    package_id: int | None
    tenant_id: int
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    """Response untuk list customers dengan pagination."""

    items: list[CustomerRead]
    total: int
    page: int
    page_size: int
    pages: int
