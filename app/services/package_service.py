"""Package service — CRUD package + sync ke tabel RADIUS group.

Phase 2: ``_sync_radius_group()`` sekarang sync atribut rate-limit untuk
**semua vendor profiles yang aktif** (bukan hanya Mikrotik-Rate-Limit).
Setiap package RADIUS group akan memiliki entry rate-limit untuk tiap vendor,
sehingga NAS dari vendor apapun bisa membaca atribut yang sesuai.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packages import Package
from app.models.radius_core import RadGroupCheck, RadGroupReply
from app.schemas.packages import PackageCreate, PackageUpdate
from app.services import vendor_profile_service


class PackageNotFoundError(Exception):
    """Package tidak ditemukan."""


class PackageGroupNameConflictError(Exception):
    """Group name RADIUS sudah dipakai package lain."""


# ---------------------------------------------------------------------------
# Internal helpers — sync ke radgroupcheck / radgroupreply
# ---------------------------------------------------------------------------


async def _sync_radius_group(db: AsyncSession, package: Package) -> None:
    """Sync atribut rate-limit ke radgroupreply untuk semua vendor profile aktif.

    Untuk setiap NasVendorProfile yang aktif, hitung nilai rate-limit sesuai
    formatnya dan insert ke radgroupreply. Entry lama dari vendor yang sama
    dihapus terlebih dahulu sebelum insert baru.

    Args:
        db: DB session.
        package: Package yang akan disync.

    """
    group = package.group_name
    up_kbps = package.speed_up_kbps
    down_kbps = package.speed_down_kbps

    # Ambil semua vendor profiles aktif
    profiles = await vendor_profile_service.get_all_active_profiles(db)

    # Kumpulkan semua nama atribut yang dikelola oleh semua vendor aktif
    # agar cleanup tidak meninggalkan atribut dari vendor yang baru dinonaktifkan
    all_managed_attrs: set[str] = set()
    for p in profiles:
        for attr in vendor_profile_service.get_all_rate_limit_attributes(p):
            all_managed_attrs.add(attr)

    # Hapus semua entry lama untuk atribut yang dikelola (dari group ini)
    if all_managed_attrs:
        result = await db.execute(
            select(RadGroupReply).where(
                RadGroupReply.groupname == group,
                RadGroupReply.attribute.in_(all_managed_attrs),
            )
        )
        for row in result.scalars().all():
            await db.delete(row)

    # Insert entry baru untuk setiap vendor aktif
    for profile in profiles:
        entries = vendor_profile_service.format_rate_limit(profile, up_kbps, down_kbps)
        for attr_name, op, value in entries:
            db.add(
                RadGroupReply(
                    groupname=group,
                    attribute=attr_name,
                    op=op,
                    value=value,
                )
            )


async def _remove_radius_group(db: AsyncSession, group_name: str) -> None:
    """Hapus semua entri radgroupcheck dan radgroupreply untuk group_name."""
    for model in (RadGroupCheck, RadGroupReply):
        result = await db.execute(
            select(model).where(model.groupname == group_name)  # type: ignore[arg-type]
        )
        for row in result.scalars().all():
            await db.delete(row)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def create_package(db: AsyncSession, data: PackageCreate) -> Package:
    """Buat package baru dan sync ke RADIUS group (semua vendor aktif).

    Args:
        db: DB session.
        data: PackageCreate payload.

    Returns:
        Package yang baru dibuat.

    Raises:
        PackageGroupNameConflictError: Jika group_name sudah dipakai.

    """
    # Cek duplikasi group_name
    existing = await db.execute(select(Package).where(Package.group_name == data.group_name))
    if existing.scalar_one_or_none():
        raise PackageGroupNameConflictError(f"Group name '{data.group_name}' sudah dipakai package lain")

    package = Package(**data.model_dump())
    db.add(package)
    await db.flush()

    # Sync ke semua vendor profile aktif
    await _sync_radius_group(db, package)

    await db.refresh(package)
    return package


async def get_package(
    db: AsyncSession,
    package_id: int,
    tenant_id: int | None = None,
) -> Package:
    """Ambil package berdasarkan ID.

    Args:
        db: DB session.
        package_id: ID package.
        tenant_id: Scope tenant (None = superadmin — bisa lihat semua).

    Returns:
        Package.

    Raises:
        PackageNotFoundError: Jika tidak ditemukan.

    """
    query = select(Package).where(Package.id == package_id)
    # Superadmin bisa lihat semua; reseller hanya bisa lihat package milik sendiri atau global
    if tenant_id is not None:
        query = query.where((Package.tenant_id == tenant_id) | (Package.tenant_id.is_(None)))

    result = await db.execute(query)
    pkg = result.scalar_one_or_none()
    if pkg is None:
        raise PackageNotFoundError(f"Package ID {package_id} tidak ditemukan")
    return pkg


async def list_packages(
    db: AsyncSession,
    tenant_id: int | None = None,
    include_inactive: bool = False,
) -> tuple[list[Package], int]:
    """List packages yang visible untuk tenant.

    Args:
        db: DB session.
        tenant_id: Scope tenant.
        include_inactive: Sertakan package non-aktif.

    Returns:
        Tuple (list of Package, total count).

    """
    query = select(Package)
    count_query = select(func.count()).select_from(Package)

    if tenant_id is not None:
        query = query.where((Package.tenant_id == tenant_id) | (Package.tenant_id.is_(None)))
        count_query = count_query.where((Package.tenant_id == tenant_id) | (Package.tenant_id.is_(None)))

    if not include_inactive:
        query = query.where(Package.is_active.is_(True))
        count_query = count_query.where(Package.is_active.is_(True))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.order_by(Package.name))
    packages = list(result.scalars().all())

    return packages, total


async def update_package(
    db: AsyncSession,
    package_id: int,
    data: PackageUpdate,
    tenant_id: int | None = None,
) -> Package:
    """Update package dan re-sync RADIUS group (semua vendor aktif).

    Args:
        db: DB session.
        package_id: ID package.
        data: PackageUpdate payload.
        tenant_id: Scope tenant.

    Returns:
        Package yang sudah diupdate.

    Raises:
        PackageNotFoundError: Jika tidak ditemukan.

    """
    package = await get_package(db, package_id, tenant_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(package, field, value)

    await db.flush()
    # Re-sync RADIUS group attributes untuk semua vendor
    await _sync_radius_group(db, package)
    await db.refresh(package)
    return package


async def delete_package(
    db: AsyncSession,
    package_id: int,
    tenant_id: int | None = None,
) -> None:
    """Hapus package dan entri RADIUS group-nya.

    Args:
        db: DB session.
        package_id: ID package.
        tenant_id: Scope tenant.

    Raises:
        PackageNotFoundError: Jika tidak ditemukan.

    """
    package = await get_package(db, package_id, tenant_id)
    await _remove_radius_group(db, package.group_name)
    await db.delete(package)
    await db.flush()
