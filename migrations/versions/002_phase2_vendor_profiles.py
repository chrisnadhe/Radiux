"""add nas_vendor_profiles and migrate nas_ext vendor column

Revision ID: 002_phase2_vendor_profiles
Revises: 001_phase1_initial
Create Date: 2026-06-18 19:00:00.000000+07:00

Perubahan:
1. Buat tabel nas_vendor_profiles dengan ENUM rate_limit_format_enum
2. Seed 6 profil vendor bawaan (Mikrotik, Ubiquiti, Cisco IOS/IOS-XE,
   Cambium, Huawei, Generic)
3. Hapus kolom `vendor` (String) dari nas_ext
4. Tambah kolom `vendor_profile_id` (FK ke nas_vendor_profiles) di nas_ext

AGENT.md rule #1: Migration ini TIDAK menyentuh tabel inti FreeRADIUS.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "002_phase2_vendor_profiles"
down_revision: str | None = "001_phase1_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Data seed — 6 profil vendor bawaan
# ---------------------------------------------------------------------------

_BUILTIN_PROFILES: list[dict[str, Any]] = [
    {
        "vendor_slug": "mikrotik",
        "name": "Mikrotik RouterOS",
        "description": (
            "Mikrotik RouterOS — menggunakan atribut Mikrotik-Rate-Limit dengan format 'down_kbps k/up_kbps k'."
        ),
        "rate_limit_attribute": "Mikrotik-Rate-Limit",
        "rate_limit_format": "mikrotik",
        "extra_group_reply_attrs": None,
        "is_builtin": True,
        "is_active": True,
    },
    {
        "vendor_slug": "ubiquiti",
        "name": "Ubiquiti (WISPr)",
        "description": (
            "Ubiquiti UniFi / AirOS — menggunakan atribut WISPr standar "
            "WISPr-Bandwidth-Max-Down (bps) dan WISPr-Bandwidth-Max-Up (bps)."
        ),
        "rate_limit_attribute": "WISPr-Bandwidth-Max-Down",
        "rate_limit_format": "bps_single_down",
        "extra_group_reply_attrs": [{"attribute": "WISPr-Bandwidth-Max-Up", "op": "=", "format": "bps_single_up"}],
        "is_builtin": True,
        "is_active": True,
    },
    {
        "vendor_slug": "cisco",
        "name": "Cisco IOS / IOS-XE",
        "description": (
            "Cisco IOS dan IOS-XE — menggunakan Cisco-AVPair dengan "
            "lcp:interface-config rate-limit untuk PPPoE/broadband subscriber. "
            "Format: rate-limit input/output {bps} {burst} {burst} "
            "conform-action transmit exceed-action drop."
        ),
        "rate_limit_attribute": "Cisco-AVPair",
        "rate_limit_format": "cisco_ios",
        "extra_group_reply_attrs": None,
        "is_builtin": True,
        "is_active": True,
    },
    {
        "vendor_slug": "cambium",
        "name": "Cambium Networks",
        "description": (
            "Cambium cnMaestro / ePMP / PMP — menggunakan atribut "
            "Cambium-Canopy-Sustained-Downlink-Rate (kbps) dan "
            "Cambium-Canopy-Sustained-Uplink-Rate (kbps)."
        ),
        "rate_limit_attribute": "Cambium-Canopy-Sustained-Downlink-Rate",
        "rate_limit_format": "kbps_single_down",
        "extra_group_reply_attrs": [
            {
                "attribute": "Cambium-Canopy-Sustained-Uplink-Rate",
                "op": "=",
                "format": "kbps_single_up",
            }
        ],
        "is_builtin": True,
        "is_active": True,
    },
    {
        "vendor_slug": "huawei",
        "name": "Huawei SmartAX / MA5800",
        "description": (
            "Huawei SmartAX dan MA5800 series — rate-limit via Huawei-Data-Filter "
            "sangat platform-specific. Profil ini sebagai placeholder; "
            "konfigurasi detail bisa ditambahkan via extra_group_reply_attrs."
        ),
        "rate_limit_attribute": None,
        "rate_limit_format": "none",
        "extra_group_reply_attrs": None,
        "is_builtin": True,
        "is_active": True,
    },
    {
        "vendor_slug": "generic",
        "name": "Generic / Standar RFC",
        "description": (
            "Profil generic — hanya autentikasi dan accounting standar. "
            "Tidak ada atribut rate-limit tambahan. Cocok untuk NAS yang "
            "menggunakan atribut RADIUS standar RFC 2865/2866 saja."
        ),
        "rate_limit_attribute": None,
        "rate_limit_format": "none",
        "extra_group_reply_attrs": None,
        "is_builtin": True,
        "is_active": True,
    },
]


def upgrade() -> None:
    """Buat tabel nas_vendor_profiles, seed data, dan migrasi nas_ext."""

    # ------------------------------------------------------------------
    # ENUM type baru
    # ------------------------------------------------------------------
    rate_limit_format_enum = sa.Enum(
        "mikrotik",
        "kbps_single_down",
        "kbps_single_up",
        "bps_single_down",
        "bps_single_up",
        "cisco_ios",
        "none",
        name="rate_limit_format_enum",
    )

    # ------------------------------------------------------------------
    # 1. Tabel nas_vendor_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "nas_vendor_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("vendor_slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rate_limit_attribute", sa.String(128), nullable=True),
        sa.Column("rate_limit_format", rate_limit_format_enum, nullable=False, server_default="none"),
        sa.Column("extra_group_reply_attrs", JSONB(), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nas_vendor_profiles_vendor_slug", "nas_vendor_profiles", ["vendor_slug"])
    op.create_index("ix_nas_vendor_profiles_is_active", "nas_vendor_profiles", ["is_active"])

    # ------------------------------------------------------------------
    # 2. Seed 6 profil vendor bawaan
    # ------------------------------------------------------------------
    profiles_table = sa.table(
        "nas_vendor_profiles",
        sa.column("vendor_slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("rate_limit_attribute", sa.String),
        sa.column("rate_limit_format", sa.String),
        sa.column("extra_group_reply_attrs", JSONB),
        sa.column("is_builtin", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(profiles_table, _BUILTIN_PROFILES)

    # ------------------------------------------------------------------
    # 3. Migrasi nas_ext: hapus kolom vendor, tambah vendor_profile_id
    # ------------------------------------------------------------------
    op.drop_column("nas_ext", "vendor")
    op.add_column(
        "nas_ext",
        sa.Column(
            "vendor_profile_id",
            sa.BigInteger(),
            sa.ForeignKey("nas_vendor_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_nas_ext_vendor_profile_id", "nas_ext", ["vendor_profile_id"])


def downgrade() -> None:
    """Kembalikan nas_ext ke kolom vendor (String) dan hapus tabel vendor profiles."""
    # Kembalikan kolom vendor (String) di nas_ext
    op.drop_index("ix_nas_ext_vendor_profile_id", table_name="nas_ext")
    op.drop_column("nas_ext", "vendor_profile_id")
    op.add_column(
        "nas_ext",
        sa.Column("vendor", sa.String(64), nullable=False, server_default="generic"),
    )

    # Hapus tabel nas_vendor_profiles
    op.drop_table("nas_vendor_profiles")

    # Drop ENUM type
    sa.Enum(name="rate_limit_format_enum").drop(op.get_bind(), checkfirst=True)
