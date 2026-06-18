"""Pydantic schemas untuk fitur Monitoring (Phase 3)."""

from datetime import datetime

from pydantic import BaseModel, Field


class ActiveSessionRead(BaseModel):
    """Data satu sesi aktif (user yang sedang online)."""

    session_id: str = Field(..., alias="acctsessionid")
    username: str
    full_name: str | None = None  # Didapat dari join tabel customers
    nas_ip_address: str = Field(..., alias="nasipaddress")
    start_time: datetime | None = Field(None, alias="acctstarttime")
    uptime_seconds: int = Field(0, alias="acctsessiontime")
    bytes_in: int = Field(0, alias="acctinputoctets")  # Download (dari NAS ke User)
    bytes_out: int = Field(0, alias="acctoutputoctets")  # Upload (dari User ke NAS)
    framed_ip_address: str | None = Field(None, alias="framedipaddress")
    mac_address: str = Field("", alias="callingstationid")

    model_config = {"populate_by_name": True, "from_attributes": True}


class NasStatusRead(BaseModel):
    """Status online/offline sebuah NAS."""

    nasname: str
    shortname: str | None = None
    is_online: bool
    last_update: datetime | None = None
    active_sessions: int = 0


class BandwidthChartData(BaseModel):
    """Data chart time-series untuk penggunaan bandwidth."""

    timestamp: datetime
    bytes_in: int
    bytes_out: int
