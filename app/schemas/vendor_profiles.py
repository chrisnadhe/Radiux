"""Pydantic schemas untuk Vendor Profile API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.nas_vendor_profiles import RateLimitFormat


class VendorProfileRead(BaseModel):
    """Response schema untuk NasVendorProfile."""

    id: int
    vendor_slug: str
    name: str
    description: str | None
    rate_limit_attribute: str | None
    rate_limit_format: RateLimitFormat
    extra_group_reply_attrs: list[Any] | None
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VendorProfileCreate(BaseModel):
    """Payload untuk membuat custom vendor profile."""

    vendor_slug: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    rate_limit_attribute: str | None = Field(None, max_length=128)
    rate_limit_format: RateLimitFormat = RateLimitFormat.NONE
    extra_group_reply_attrs: list[dict[str, str]] | None = None


class VendorProfileUpdate(BaseModel):
    """Payload update vendor profile — semua field opsional.

    vendor_slug dan is_builtin tidak bisa diubah lewat API.
    """

    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    rate_limit_attribute: str | None = Field(None, max_length=128)
    rate_limit_format: RateLimitFormat | None = None
    extra_group_reply_attrs: list[dict[str, str]] | None = None
    is_active: bool | None = None


class VendorProfileListResponse(BaseModel):
    """Response untuk list vendor profiles."""

    items: list[VendorProfileRead]
    total: int
