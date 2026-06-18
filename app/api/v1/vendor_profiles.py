"""Router Vendor Profiles — CRUD profil vendor NAS."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUserId, DbSession
from app.schemas.vendor_profiles import (
    VendorProfileCreate,
    VendorProfileListResponse,
    VendorProfileRead,
    VendorProfileUpdate,
)
from app.services import vendor_profile_service

router = APIRouter(prefix="/vendor-profiles", tags=["Vendor Profiles"])


@router.get("", response_model=VendorProfileListResponse, summary="List Vendor Profiles")
async def list_vendor_profiles(
    db: DbSession,
    user_id: CurrentUserId,
    include_inactive: bool = False,
) -> VendorProfileListResponse:
    """List semua vendor profiles (bawaan dan kustom)."""
    profiles, total = await vendor_profile_service.list_vendor_profiles(db, include_inactive=include_inactive)
    return VendorProfileListResponse(
        items=[VendorProfileRead.model_validate(p) for p in profiles],
        total=total,
    )


@router.get("/{profile_id}", response_model=VendorProfileRead, summary="Detail Vendor Profile")
async def get_vendor_profile(
    profile_id: int,
    db: DbSession,
    user_id: CurrentUserId,
) -> VendorProfileRead:
    """Ambil detail satu vendor profile berdasarkan ID."""
    try:
        profile = await vendor_profile_service.get_vendor_profile(db, profile_id)
    except vendor_profile_service.VendorProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return VendorProfileRead.model_validate(profile)


@router.post(
    "",
    response_model=VendorProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Buat Custom Vendor Profile",
)
async def create_vendor_profile(
    data: VendorProfileCreate,
    db: DbSession,
    user_id: CurrentUserId,
) -> VendorProfileRead:
    """Buat vendor profile kustom baru (hanya superadmin)."""
    try:
        profile = await vendor_profile_service.create_vendor_profile(db, data)
    except vendor_profile_service.VendorProfileSlugConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return VendorProfileRead.model_validate(profile)


@router.patch("/{profile_id}", response_model=VendorProfileRead, summary="Update Vendor Profile")
async def update_vendor_profile(
    profile_id: int,
    data: VendorProfileUpdate,
    db: DbSession,
    user_id: CurrentUserId,
) -> VendorProfileRead:
    """Update vendor profile (builtin bisa diubah nama/deskripsi/is_active, slug tidak)."""
    try:
        profile = await vendor_profile_service.update_vendor_profile(db, profile_id, data)
    except vendor_profile_service.VendorProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return VendorProfileRead.model_validate(profile)


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hapus Custom Vendor Profile",
)
async def delete_vendor_profile(
    profile_id: int,
    db: DbSession,
    user_id: CurrentUserId,
) -> None:
    """Hapus vendor profile kustom. Profil bawaan (is_builtin=True) tidak bisa dihapus."""
    try:
        await vendor_profile_service.delete_vendor_profile(db, profile_id)
    except vendor_profile_service.VendorProfileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except vendor_profile_service.VendorProfileBuiltinError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
