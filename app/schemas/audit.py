"""Pydantic schemas untuk Audit Logs (Phase 9)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    """Schema output untuk Audit Log."""

    id: int
    user_id: int | None
    action: str
    table_name: str | None
    record_id: str | None
    details: dict[str, Any]
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Schema untuk list Audit Logs dengan pagination."""

    items: list[AuditLogRead]
    total: int
    page: int
    page_size: int
    pages: int
