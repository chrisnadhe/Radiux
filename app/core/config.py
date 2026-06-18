"""Konfigurasi aplikasi Radiux via pydantic-settings."""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Semua konfigurasi aplikasi dibaca dari environment / file .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    app_env: str = "development"
    debug: bool = False
    secret_key: str
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]

    # -----------------------------------------------------------------------
    # Database
    # -----------------------------------------------------------------------
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "radiux_db"
    postgres_user: str = "radiux_user"
    postgres_password: str

    # Database URL — dibentuk otomatis dari field di atas jika tidak di-override
    database_url: PostgresDsn | None = None

    @model_validator(mode="before")
    @classmethod
    def assemble_db_url(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Bentuk DATABASE_URL dari komponen individual jika belum ada."""
        if not values.get("database_url"):
            host = values.get("postgres_host", "postgres")
            port = values.get("postgres_port", 5432)
            db = values.get("postgres_db", "radiux_db")
            user = values.get("postgres_user", "radiux_user")
            password = values.get("postgres_password", "")
            values["database_url"] = (
                f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"
            )
        return values

    # -----------------------------------------------------------------------
    # RADIUS
    # -----------------------------------------------------------------------
    # Default kosong — wajib diisi via .env di production
    radius_default_secret: str = ""  # noqa: S105

    # -----------------------------------------------------------------------
    # Redis
    # -----------------------------------------------------------------------
    redis_url: RedisDsn = "redis://redis:6379/0"  # type: ignore[assignment]

    # -----------------------------------------------------------------------
    # JWT
    # -----------------------------------------------------------------------
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # -----------------------------------------------------------------------
    # App metadata
    # -----------------------------------------------------------------------
    app_name: str = "Radiux"
    app_version: str = "0.1.0"
    app_description: str = (
        "Web UI modern untuk mengelola FreeRADIUS — "
        "AAA, Hotspot, Billing/Voucher, dan Multi-Reseller untuk ISP"
    )

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        """Izinkan ALLOWED_HOSTS sebagai comma-separated string di .env."""
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return singleton Settings — di-cache agar tidak baca file berulang."""
    return Settings()
