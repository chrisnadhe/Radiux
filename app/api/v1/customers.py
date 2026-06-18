"""Router customers — CRUD pelanggan dengan RADIUS provisioning."""

import math

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DbSession
from app.models.customers import CustomerStatus
from app.schemas.customers import (
    CustomerCreate,
    CustomerListResponse,
    CustomerRead,
    CustomerUpdate,
)
from app.services import customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


def _get_tenant_id(user: "AdminUser") -> int | None:
    """Return tenant_id for scoping based on user role."""
    if user.is_superadmin:
        return None  # Superadmin can view all or filter specifically (not fully implemented yet)
    return user.tenant_id


@router.get("", response_model=CustomerListResponse, summary="List customers")
async def list_customers(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=128),
    status: CustomerStatus | None = None,
) -> CustomerListResponse:
    """List customers dengan pagination dan optional search/filter."""
    tenant_id = _get_tenant_id(user)
    customers, total = await customer_service.list_customers(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
    )
    pages = math.ceil(total / page_size) if total else 0
    return CustomerListResponse(
        items=[CustomerRead.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Buat customer baru",
)
async def create_customer(
    data: CustomerCreate,
    db: DbSession,
    user: CurrentUser,
) -> CustomerRead:
    """Buat customer baru dan provision otomatis ke FreeRADIUS."""
    # Enforce tenant_id for resellers
    if not user.is_superadmin:
        data.tenant_id = user.tenant_id

    try:
        customer = await customer_service.create_customer(db, data)
    except customer_service.CustomerUsernameConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    return CustomerRead.model_validate(customer)


@router.get("/{customer_id}", response_model=CustomerRead, summary="Detail customer")
async def get_customer(
    customer_id: int,
    db: DbSession,
    user: CurrentUser,
) -> CustomerRead:
    """Ambil detail satu customer berdasarkan ID."""
    tenant_id = _get_tenant_id(user)
    try:
        customer = await customer_service.get_customer(db, customer_id, tenant_id)
    except customer_service.CustomerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CustomerRead.model_validate(customer)


@router.patch("/{customer_id}", response_model=CustomerRead, summary="Update customer")
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: DbSession,
    user: CurrentUser,
) -> CustomerRead:
    """Update data customer dan re-provision RADIUS jika diperlukan."""
    tenant_id = _get_tenant_id(user)
    try:
        customer = await customer_service.update_customer(db, customer_id, data, tenant_id)
    except customer_service.CustomerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    return CustomerRead.model_validate(customer)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hapus customer")
async def delete_customer(
    customer_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Hapus customer dan semua data RADIUS-nya."""
    tenant_id = _get_tenant_id(user)
    try:
        await customer_service.delete_customer(db, customer_id, tenant_id)
    except customer_service.CustomerNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
