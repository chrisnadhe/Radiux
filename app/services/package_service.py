"""Package service — CRUD package + sync ke tabel RADIUS group."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packages import Package
from app.models.radius_core import RadGroupCheck, RadGroupReply
from app.schemas.packages import PackageCreate, PackageUpdate


class PackageNotFoundError(Exception):
    """Package tidak ditemukan."""


class PackageGroupNameConflictError(Exception):
    """Group name RADIUS sudah dipakai package lain."""


# ---------------------------------------------------------------------------
# Internal helpers — sync ke radgroupcheck / radgroupreply
# ---------------------------------------------------------------------------


def _kbps_to_rate_limit_str(up_kbps: int, down_kbps: int) -> str:
    """Format Mikrotik-Rate-Limit string dari upload/download Kbps.

    Format: ``{down}k/{up}k`` (sesuai konvensi Mikrotik).
    Dipakai sebagai placeholder generic — Phase 2 akan handle per-vendor.

    Args:
        up_kbps: Upload speed Kbps (0 = unlimited).
        down_kbps: Download speed Kbps (0 = unlimited).

    Returns:
        Rate limit string, contoh: ``10240k/5120k``.

    """
    up = f"{up_kbps}k" if up_kbps > 0 else "0"
    down = f"{down_kbps}k" if down_kbps > 0 else "0"
    return f"{down}/{up}"


async def _sync_radius_group(db: AsyncSession, package: Package) -> None:
    """Sync atribut bandwidth ke radgroupreply untuk group_name package.

    Saat ini hanya sync Mikrotik-Rate-Limit (generic placeholder).
    Phase 2 akan diganti dengan vendor profile abstraction.

    Args:
        db: DB session.
        package: Package yang akan disync.

    """
    group = package.group_name
    rate_limit = _kbps_to_rate_limit_str(package.speed_up_kbps, package.speed_down_kbps)

    # Hapus reply lama untuk group ini
    result = await db.execute(
        select(RadGroupReply).where(
            RadGroupReply.groupname == group,
            RadGroupReply.attribute == "Mikrotik-Rate-Limit",
        )
    )
    for row in result.scalars().all():
        await db.delete(row)

    # Buat entry baru (hanya jika ada speed limit)
    if package.speed_up_kbps > 0 or package.speed_down_kbps > 0:
        db.add(
            RadGroupReply(
                groupname=group,
                attribute="Mikrotik-Rate-Limit",
                op="=",
                value=rate_limit,
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
    """Buat package baru dan sync ke RADIUS group.

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

    # Sync ke RADIUS group
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
    """Update package dan re-sync RADIUS group.

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
    # Re-sync RADIUS group attributes
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
