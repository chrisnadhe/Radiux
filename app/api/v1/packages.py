"""Router packages — CRUD paket layanan dengan RADIUS group sync."""

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession, SuperAdminUser
from app.schemas.packages import (
    PackageCreate,
    PackageListResponse,
    PackageRead,
    PackageUpdate,
)
from app.services import package_service

router = APIRouter(prefix="/packages", tags=["Packages"])


@router.get("", response_model=PackageListResponse, summary="List packages")
async def list_packages(
    db: DbSession,
    user: CurrentUser,
    include_inactive: bool = Query(False),
) -> PackageListResponse:
    """List semua package yang visible untuk user yang login."""
    # For phase 6, all tenants can view all packages. If packages become tenant-specific, we will scope it here.
    packages, total = await package_service.list_packages(db, tenant_id=None, include_inactive=include_inactive)
    return PackageListResponse(
        items=[PackageRead.model_validate(p) for p in packages],
        total=total,
    )


@router.post(
    "",
    response_model=PackageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Buat package baru",
)
async def create_package(
    data: PackageCreate,
    db: DbSession,
    user: SuperAdminUser,
) -> PackageRead:
    """Buat package baru dan sync ke RADIUS group."""
    try:
        package = await package_service.create_package(db, data)
    except package_service.PackageGroupNameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return PackageRead.model_validate(package)


@router.get("/{package_id}", response_model=PackageRead, summary="Detail package")
async def get_package(
    package_id: int,
    db: DbSession,
    user: CurrentUser,
) -> PackageRead:
    """Ambil detail satu package."""
    try:
        package = await package_service.get_package(db, package_id)
    except package_service.PackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return PackageRead.model_validate(package)


@router.patch("/{package_id}", response_model=PackageRead, summary="Update package")
async def update_package(
    package_id: int,
    data: PackageUpdate,
    db: DbSession,
    user: SuperAdminUser,
) -> PackageRead:
    """Update package dan re-sync RADIUS group attributes."""
    try:
        package = await package_service.update_package(db, package_id, data)
    except package_service.PackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return PackageRead.model_validate(package)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus package")
async def delete_package(
    package_id: int,
    db: DbSession,
    user: SuperAdminUser,
) -> None:
    """Hapus package dan entri RADIUS group-nya."""
    try:
        await package_service.delete_package(db, package_id)
    except package_service.PackageNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
