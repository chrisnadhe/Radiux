"""Router NAS — CRUD Network Access Server dengan enkripsi shared secret."""

from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, SuperAdminUser
from app.models.nas_ext import NasExt
from app.schemas.nas import NasCreateRequest, NasListResponse, NasRead, NasUpdateRequest
from app.schemas.vendor_profiles import VendorProfileRead
from app.services import nas_service

router = APIRouter(prefix="/nas", tags=["NAS"])


def _build_nas_read(nas_core: object, nas_ext: NasExt) -> NasRead:
    """Bangun NasRead response dari pasangan NasCore + NasExt.

    shared_secret TIDAK disertakan di response (AGENT.md rule #3).
    """
    vendor_profile_read = None
    if nas_ext.vendor_profile is not None:
        vendor_profile_read = VendorProfileRead.model_validate(nas_ext.vendor_profile)

    return NasRead(
        id=nas_ext.id,
        nasname=nas_ext.nasname,
        shortname=getattr(nas_core, "shortname", ""),
        nas_type=getattr(nas_core, "type", "other"),
        ports=getattr(nas_core, "ports", None),
        description=getattr(nas_core, "description", None),
        vendor_profile_id=nas_ext.vendor_profile_id,
        vendor_profile=vendor_profile_read,
        location=nas_ext.location,
        is_active=nas_ext.is_active,
        tenant_id=nas_ext.tenant_id,
        created_at=nas_ext.created_at,
        updated_at=nas_ext.updated_at,
    )


@router.get("", response_model=NasListResponse, summary="List NAS")
async def list_nas(
    db: DbSession,
    user_id: SuperAdminUser,
) -> NasListResponse:
    """List semua NAS yang visible untuk user."""
    pairs, total = await nas_service.list_nas(db, tenant_id=None)
    return NasListResponse(
        items=[_build_nas_read(core, ext) for core, ext in pairs],
        total=total,
    )


@router.post(
    "",
    response_model=NasRead,
    status_code=status.HTTP_201_CREATED,
    summary="Daftarkan NAS baru",
)
async def create_nas(
    data: NasCreateRequest,
    db: DbSession,
    user_id: SuperAdminUser,
) -> NasRead:
    """Daftarkan NAS baru dengan enkripsi shared secret otomatis."""
    try:
        nas_core, nas_ext = await nas_service.create_nas(db, data)
    except nas_service.NasNasnameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return _build_nas_read(nas_core, nas_ext)


@router.get("/{nas_id}", response_model=NasRead, summary="Detail NAS")
async def get_nas(
    nas_id: int,
    db: DbSession,
    user_id: SuperAdminUser,
) -> NasRead:
    """Ambil detail NAS berdasarkan ID."""
    try:
        nas_core, nas_ext = await nas_service.get_nas(db, nas_id)
    except nas_service.NasNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _build_nas_read(nas_core, nas_ext)


@router.patch("/{nas_id}", response_model=NasRead, summary="Update NAS")
async def update_nas(
    nas_id: int,
    data: NasUpdateRequest,
    db: DbSession,
    user_id: SuperAdminUser,
) -> NasRead:
    """Update NAS — shared_secret baru akan dienkripsi otomatis."""
    try:
        nas_core, nas_ext = await nas_service.update_nas(db, nas_id, data)
    except nas_service.NasNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return _build_nas_read(nas_core, nas_ext)


@router.delete("/{nas_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus NAS")
async def delete_nas(
    nas_id: int,
    db: DbSession,
    user_id: SuperAdminUser,
) -> None:
    """Hapus NAS dari sistem (NasCore + NasExt)."""
    try:
        await nas_service.delete_nas(db, nas_id)
    except nas_service.NasNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
