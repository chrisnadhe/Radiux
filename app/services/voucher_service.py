"""Service layer untuk operasi pembuatan dan ekspor Voucher Prabayar."""

import logging
import secrets
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customers import Customer, CustomerStatus
from app.models.packages import Package
from app.models.radius_core import RadCheck, RadUserGroup
from app.models.vouchers import VoucherBatch
from app.services import wallet_service

logger = logging.getLogger(__name__)


def generate_random_code(length: int = 6) -> str:
    """Generate random string mengabaikan karakter yang membingungkan."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(chars) for _ in range(length))


async def create_voucher_batch(
    db: AsyncSession,
    name: str,
    qty: int,
    package_id: int,
    tenant_id: int,
    length: int = 6,
    prefix: str = "",
    notes: str | None = None,
) -> VoucherBatch:
    """Membuat sejumlah voucher baru dan menyimpannya ke DB."""

    # Validasi paket
    pkg = await db.scalar(select(Package).where(Package.id == package_id))
    if not pkg:
        raise ValueError("Package tidak ditemukan")

    total_cost = float(pkg.price) * qty

    # Lakukan pemotongan saldo wallet (akan throw InsufficientBalanceError jika gagal)
    if total_cost > 0:
        await wallet_service.deduct_balance(
            db=db, tenant_id=tenant_id, amount=total_cost, notes=f"Generate {qty} voucher untuk paket {pkg.name}"
        )

    # Buat record Batch
    batch = VoucherBatch(
        name=name, quantity=qty, length=length, prefix=prefix, notes=notes, package_id=package_id, tenant_id=tenant_id
    )
    db.add(batch)
    await db.flush()  # untuk mendapatkan batch.id

    vouchers_created = 0
    max_attempts = qty * 3
    attempts = 0

    # Generate username & password
    while vouchers_created < qty and attempts < max_attempts:
        attempts += 1
        username = f"{prefix}{generate_random_code(length)}"
        password = generate_random_code(length)

        # Cek duplikat username di radcheck
        exist = await db.scalar(select(RadCheck).where(RadCheck.username == username))
        if exist:
            continue

        # 1. Simpan ke Customer (is_voucher=True)
        # Nama default bisa sama dengan username
        customer = Customer(
            radius_username=username,
            full_name=f"Voucher {username}",
            is_voucher=True,
            voucher_batch_id=batch.id,
            voucher_password=password,
            package_id=package_id,
            tenant_id=tenant_id,
            status=CustomerStatus.INACTIVE,  # Voucher belum aktif sampai login pertama
            is_active=True,
        )
        db.add(customer)

        # 2. Simpan ke RadCheck (Cleartext-Password)
        radcheck = RadCheck(username=username, attribute="Cleartext-Password", op=":=", value=password)
        db.add(radcheck)

        # 3. Simpan ke RadUserGroup
        radusergroup = RadUserGroup(username=username, groupname=pkg.group_name, priority=10)
        db.add(radusergroup)

        vouchers_created += 1

    if vouchers_created < qty:
        logger.warning(f"Hanya bisa generate {vouchers_created} dari {qty} voucher setelah {attempts} percobaan.")

    await db.commit()
    await db.refresh(batch)
    return batch


async def get_voucher_batches(db: AsyncSession, tenant_id: int) -> Sequence[VoucherBatch]:
    """Mendapatkan daftar semua batch voucher milik tenant."""
    result = await db.scalars(
        select(VoucherBatch).where(VoucherBatch.tenant_id == tenant_id).order_by(VoucherBatch.created_at.desc())
    )
    return result.all()


async def get_vouchers_by_batch(db: AsyncSession, batch_id: int, tenant_id: int) -> Sequence[Customer]:
    """Mendapatkan daftar customer (voucher) spesifik berdasarkan batch."""
    result = await db.scalars(
        select(Customer)
        .where(Customer.voucher_batch_id == batch_id)
        .where(Customer.tenant_id == tenant_id)
        .order_by(Customer.id)
    )
    return result.all()
