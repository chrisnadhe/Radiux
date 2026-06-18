"""Pydantic schemas untuk NAS CRUD."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.vendor_profiles import VendorProfileRead


class NasCreateRequest(BaseModel):
    """Payload untuk mendaftarkan NAS baru.

    shared_secret dikirim plain dari client, akan dienkripsi sebelum disimpan.
    """

    nasname: str = Field(
        ...,
        description="IP address atau hostname NAS",
        min_length=1,
        max_length=128,
    )
    shortname: str = Field(..., min_length=1, max_length=32)
    nas_type: str = Field("other", max_length=30, alias="type")
    ports: int | None = Field(None, ge=1, le=65535)
    # Plain text — akan dienkripsi di service layer (AGENT.md rule #3)
    shared_secret: str = Field(..., min_length=1, max_length=60)
    description: str | None = Field(None, max_length=200)
    # vendor_profile_id = None → pakai profil 'generic' (autentikasi saja)
    vendor_profile_id: int | None = None
    location: str | None = Field(None, max_length=256)
    tenant_id: int | None = None

    model_config = {"populate_by_name": True}

    @field_validator("vendor_profile_id", "ports", mode="before")
    @classmethod
    def empty_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v


class NasUpdateRequest(BaseModel):
    """Payload update NAS — semua field opsional."""

    shortname: str | None = Field(None, min_length=1, max_length=32)
    nas_type: str | None = Field(None, max_length=30, alias="type")
    ports: int | None = Field(None, ge=1, le=65535)
    # None berarti tidak ganti shared secret
    shared_secret: str | None = Field(None, min_length=1, max_length=60)
    description: str | None = None
    vendor_profile_id: int | None = None
    location: str | None = None
    is_active: bool | None = None

    model_config = {"populate_by_name": True}

    @field_validator("vendor_profile_id", "ports", "shared_secret", mode="before")
    @classmethod
    def empty_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v


class NasRead(BaseModel):
    """Response NAS — shared_secret TIDAK pernah dikembalikan ke client."""

    id: int
    nasname: str
    shortname: str
    nas_type: str
    ports: int | None
    description: str | None
    vendor_profile_id: int | None
    vendor_profile: VendorProfileRead | None = None
    location: str | None
    is_active: bool
    tenant_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NasListResponse(BaseModel):
    """Response untuk list NAS."""

    items: list[NasRead]
    total: int
