"""create radiux extension tables

Revision ID: 001_phase1_initial
Revises:
Create Date: 2026-06-18 18:00:00.000000+07:00

PENTING: Migration ini HANYA membuat tabel ekstensi Radiux.
Tabel inti FreeRADIUS (radcheck, radreply, dll.) dibuat via
docker/postgres/init/01_freeradius_schema.sql — bukan di sini.
Lihat AGENT.md rule #1 dan migrations/env.py _include_name filter.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_phase1_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Buat tabel ekstensi Radiux: tenants, admin_users, packages, customers, nas_ext."""

    # ------------------------------------------------------------------
    # ENUM types
    # ------------------------------------------------------------------
    tenant_status_enum = sa.Enum("active", "suspended", "inactive", name="tenant_status_enum")
    admin_role_enum = sa.Enum("superadmin", "reseller", "operator", "viewer", name="admin_role_enum")
    package_type_enum = sa.Enum("prepaid", "postpaid", name="package_type_enum")
    customer_status_enum = sa.Enum("active", "suspended", "expired", "inactive", name="customer_status_enum")

    # ------------------------------------------------------------------
    # 1. tenants
    # ------------------------------------------------------------------
    op.create_table(
        "tenants",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("status", tenant_status_enum, nullable=False, server_default="active"),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_name", "tenants", ["name"])
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    # ------------------------------------------------------------------
    # 2. admin_users
    # ------------------------------------------------------------------
    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(128), nullable=False),
        sa.Column("full_name", sa.String(128), nullable=True),
        sa.Column("role", admin_role_enum, nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"])
    op.create_index("ix_admin_users_email", "admin_users", ["email"])
    op.create_index("ix_admin_users_tenant_id", "admin_users", ["tenant_id"])

    # ------------------------------------------------------------------
    # 3. packages
    # ------------------------------------------------------------------
    op.create_table(
        "packages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("group_name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_type", package_type_enum, nullable=False, server_default="prepaid"),
        sa.Column("speed_up_kbps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("speed_down_kbps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quota_mb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_packages_name", "packages", ["name"])
    op.create_index("ix_packages_group_name", "packages", ["group_name"])
    op.create_index("ix_packages_tenant_id", "packages", ["tenant_id"])

    # ------------------------------------------------------------------
    # 4. customers
    # ------------------------------------------------------------------
    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("radius_username", sa.String(64), nullable=False, unique=True),
        sa.Column("full_name", sa.String(128), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", customer_status_enum, nullable=False, server_default="active"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("package_id", sa.BigInteger(), sa.ForeignKey("packages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_customers_radius_username", "customers", ["radius_username"])
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_status", "customers", ["status"])
    op.create_index("ix_customers_package_id", "customers", ["package_id"])
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])
    op.create_index("ix_customers_expires_at", "customers", ["expires_at"])

    # ------------------------------------------------------------------
    # 5. nas_ext
    # ------------------------------------------------------------------
    op.create_table(
        "nas_ext",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("nasname", sa.String(128), nullable=False, unique=True),
        sa.Column("vendor", sa.String(64), nullable=False, server_default="generic"),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("tenant_id", sa.BigInteger(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_nas_ext_nasname", "nas_ext", ["nasname"])
    op.create_index("ix_nas_ext_tenant_id", "nas_ext", ["tenant_id"])


def downgrade() -> None:
    """Drop semua tabel ekstensi Radiux (urutan terbalik untuk FK)."""
    op.drop_table("nas_ext")
    op.drop_table("customers")
    op.drop_table("packages")
    op.drop_table("admin_users")
    op.drop_table("tenants")

    # Drop ENUM types
    sa.Enum(name="customer_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="package_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="admin_role_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tenant_status_enum").drop(op.get_bind(), checkfirst=True)
