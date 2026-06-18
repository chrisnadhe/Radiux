"""Pydantic schemas untuk Package CRUD."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.packages import PackageType


class PackageBase(BaseModel):
    """Field yang dipakai di Create dan Update."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    package_type: PackageType = PackageType.PREPAID
    speed_up_kbps: int = Field(0, ge=0, description="Upload speed dalam Kbps; 0 = unlimited")
    speed_down_kbps: int = Field(0, ge=0, description="Download speed dalam Kbps; 0 = unlimited")
    quota_mb: int = Field(0, ge=0, description="Kuota dalam MB; 0 = unlimited")
    validity_days: int = Field(30, ge=0, description="Masa berlaku dalam hari; 0 = tidak ada expiry")
    price: float = Field(0.0, ge=0)
    is_active: bool = True
    tenant_id: int | None = None


class PackageCreate(PackageBase):
    """Payload untuk membuat package baru."""

    group_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9._-]+$",
        description="Nama grup RADIUS (dipakai di radgroupcheck/radgroupreply)",
    )

    @field_validator("group_name")
    @classmethod
    def group_name_lowercase(cls, v: str) -> str:
        """Konversi group_name ke lowercase agar konsisten."""
        return v.lower()


class PackageUpdate(BaseModel):
    """Payload untuk update package — semua field opsional."""

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    speed_up_kbps: int | None = Field(None, ge=0)
    speed_down_kbps: int | None = Field(None, ge=0)
    quota_mb: int | None = Field(None, ge=0)
    validity_days: int | None = Field(None, ge=0)
    price: float | None = Field(None, ge=0)
    is_active: bool | None = None


class PackageRead(PackageBase):
    """Response schema Package."""

    id: int
    group_name: str
    speed_up_mbps: float
    speed_down_mbps: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackageListResponse(BaseModel):
    """Response untuk list packages."""

    items: list[PackageRead]
    total: int
