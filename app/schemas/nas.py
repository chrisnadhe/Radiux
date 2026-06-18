"""Pydantic schemas untuk NAS CRUD."""

from datetime import datetime

from pydantic import BaseModel, Field


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
    vendor: str = Field("generic", max_length=64)
    location: str | None = Field(None, max_length=256)
    tenant_id: int | None = None

    model_config = {"populate_by_name": True}


class NasUpdateRequest(BaseModel):
    """Payload update NAS — semua field opsional."""

    shortname: str | None = Field(None, min_length=1, max_length=32)
    nas_type: str | None = Field(None, max_length=30, alias="type")
    ports: int | None = Field(None, ge=1, le=65535)
    # None berarti tidak ganti shared secret
    shared_secret: str | None = Field(None, min_length=1, max_length=60)
    description: str | None = None
    vendor: str | None = None
    location: str | None = None
    is_active: bool | None = None

    model_config = {"populate_by_name": True}


class NasRead(BaseModel):
    """Response NAS — shared_secret TIDAK pernah dikembalikan ke client."""

    id: int
    nasname: str
    shortname: str
    nas_type: str
    ports: int | None
    description: str | None
    vendor: str
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
