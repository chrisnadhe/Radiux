"""Customer service — CRUD customer + provisioning ke tabel RADIUS."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customers import Customer, CustomerStatus
from app.models.packages import Package
from app.models.radius_core import RadCheck, RadUserGroup
from app.schemas.customers import CustomerCreate, CustomerUpdate


class CustomerNotFoundError(Exception):
    """Customer tidak ditemukan."""


class CustomerUsernameConflictError(Exception):
    """Radius username sudah dipakai."""


# ---------------------------------------------------------------------------
# Internal helpers — provisioning ke tabel RADIUS
# ---------------------------------------------------------------------------


async def _provision_radius_user(
    db: AsyncSession,
    radius_username: str,
    radius_password: str,
) -> None:
    """Buat atau update entry radcheck untuk autentikasi PAP.

    Args:
        db: DB session.
        radius_username: Username RADIUS.
        radius_password: Password plain text (disimpan di radcheck value).

    """
    # Cek apakah sudah ada entri password
    result = await db.execute(
        select(RadCheck).where(
            RadCheck.username == radius_username,
            RadCheck.attribute == "Cleartext-Password",
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = radius_password
    else:
        db.add(
            RadCheck(
                username=radius_username,
                attribute="Cleartext-Password",
                op=":=",
                value=radius_password,
            )
        )


async def _provision_radius_group(
    db: AsyncSession,
    radius_username: str,
    group_name: str,
) -> None:
    """Assign user ke grup RADIUS (package group) di radusergroup.

    Hapus assignment lama dulu, lalu buat yang baru.

    Args:
        db: DB session.
        radius_username: Username RADIUS.
        group_name: Nama grup/package RADIUS.

    """
    # Hapus assignment lama
    result = await db.execute(select(RadUserGroup).where(RadUserGroup.username == radius_username))
    for old in result.scalars().all():
        await db.delete(old)

    # Buat assignment baru
    db.add(
        RadUserGroup(
            username=radius_username,
            groupname=group_name,
            priority=1,
        )
    )


async def _deprovision_radius_user(db: AsyncSession, radius_username: str) -> None:
    """Hapus semua entri RADIUS untuk user yang dihapus/dinonaktifkan."""
    # Hapus radcheck
    result = await db.execute(select(RadCheck).where(RadCheck.username == radius_username))
    for row in result.scalars().all():
        await db.delete(row)

    # Hapus radusergroup
    result = await db.execute(select(RadUserGroup).where(RadUserGroup.username == radius_username))
    for row in result.scalars().all():
        await db.delete(row)


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def create_customer(
    db: AsyncSession,
    data: CustomerCreate,
) -> Customer:
    """Buat customer baru dan provision ke RADIUS.

    Args:
        db: DB session.
        data: CustomerCreate payload.

    Returns:
        Customer yang baru dibuat.

    Raises:
        CustomerUsernameConflictError: Jika radius_username sudah dipakai.

    """
    # Cek duplikasi username
    existing = await db.execute(select(Customer).where(Customer.radius_username == data.radius_username))
    if existing.scalar_one_or_none():
        raise CustomerUsernameConflictError(f"Username RADIUS '{data.radius_username}' sudah dipakai")

    # Hitung expires_at dari validity package
    expires_at: datetime | None = None
    if data.package_id:
        pkg_result = await db.execute(select(Package).where(Package.id == data.package_id))
        pkg = pkg_result.scalar_one_or_none()
        if pkg and pkg.validity_days > 0:
            expires_at = datetime.now(UTC) + timedelta(days=pkg.validity_days)

    customer = Customer(
        radius_username=data.radius_username,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        address=data.address,
        notes=data.notes,
        telegram_chat_id=data.telegram_chat_id,
        status=CustomerStatus.ACTIVE,
        is_active=True,
        package_id=data.package_id,
        tenant_id=data.tenant_id,
        expires_at=expires_at,
    )
    db.add(customer)
    await db.flush()

    # Provision ke RADIUS
    await _provision_radius_user(db, data.radius_username, data.radius_password)
    if data.package_id and pkg:  # type: ignore[possibly-undefined]
        await _provision_radius_group(db, data.radius_username, pkg.group_name)

    await db.refresh(customer)
    return customer


async def get_customer(
    db: AsyncSession,
    customer_id: int,
    tenant_id: int | None = None,
) -> Customer:
    """Ambil customer berdasarkan ID, dengan scope tenant_id.

    Args:
        db: DB session.
        customer_id: ID customer.
        tenant_id: Jika None, superadmin (tidak ada filter tenant).

    Returns:
        Customer.

    Raises:
        CustomerNotFoundError: Jika tidak ditemukan.

    """
    query = select(Customer).where(Customer.id == customer_id)
    if tenant_id is not None:
        query = query.where(Customer.tenant_id == tenant_id)

    result = await db.execute(query)
    customer = result.scalar_one_or_none()
    if customer is None:
        raise CustomerNotFoundError(f"Customer ID {customer_id} tidak ditemukan")
    return customer


async def list_customers(
    db: AsyncSession,
    tenant_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    status: CustomerStatus | None = None,
) -> tuple[list[Customer], int]:
    """List customers dengan filtering dan pagination.

    Args:
        db: DB session.
        tenant_id: Scope tenant (None = superadmin, semua tenant).
        page: Halaman (1-indexed).
        page_size: Jumlah item per halaman.
        search: Cari berdasarkan full_name atau radius_username.
        status: Filter status.

    Returns:
        Tuple (list of Customer, total count).

    """
    query = select(Customer)
    count_query = select(func.count()).select_from(Customer)

    if tenant_id is not None:
        query = query.where(Customer.tenant_id == tenant_id)
        count_query = count_query.where(Customer.tenant_id == tenant_id)

    if search:
        like = f"%{search}%"
        query = query.where(Customer.full_name.ilike(like) | Customer.radius_username.ilike(like))
        count_query = count_query.where(Customer.full_name.ilike(like) | Customer.radius_username.ilike(like))

    if status:
        query = query.where(Customer.status == status)
        count_query = count_query.where(Customer.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Customer.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    customers = list(result.scalars().all())

    return customers, total


async def update_customer(
    db: AsyncSession,
    customer_id: int,
    data: CustomerUpdate,
    tenant_id: int | None = None,
) -> Customer:
    """Update customer dan re-provision RADIUS jika paket/password berubah.

    Args:
        db: DB session.
        customer_id: ID customer yang akan diupdate.
        data: CustomerUpdate payload (partial update).
        tenant_id: Scope tenant.

    Returns:
        Customer yang sudah diupdate.

    Raises:
        CustomerNotFoundError: Jika tidak ditemukan.

    """
    customer = await get_customer(db, customer_id, tenant_id)

    update_data = data.model_dump(exclude_none=True, exclude={"radius_password"})

    # Hitung expires_at baru jika package berubah
    if "package_id" in update_data and update_data["package_id"] != customer.package_id:
        pkg_result = await db.execute(select(Package).where(Package.id == update_data["package_id"]))
        pkg = pkg_result.scalar_one_or_none()
        if pkg and pkg.validity_days > 0:
            customer.expires_at = datetime.now(UTC) + timedelta(days=pkg.validity_days)
        # Re-provision group
        if pkg:
            await _provision_radius_group(db, customer.radius_username, pkg.group_name)

    for field, value in update_data.items():
        setattr(customer, field, value)

    # Update password jika disertakan
    if data.radius_password:
        await _provision_radius_user(db, customer.radius_username, data.radius_password)

    await db.flush()
    await db.refresh(customer)
    return customer


async def delete_customer(
    db: AsyncSession,
    customer_id: int,
    tenant_id: int | None = None,
) -> None:
    """Hapus customer dan semua data RADIUS-nya.

    Args:
        db: DB session.
        customer_id: ID customer yang akan dihapus.
        tenant_id: Scope tenant.

    Raises:
        CustomerNotFoundError: Jika tidak ditemukan.

    """
    customer = await get_customer(db, customer_id, tenant_id)
    await _deprovision_radius_user(db, customer.radius_username)
    await db.delete(customer)
    await db.flush()
