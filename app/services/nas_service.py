"""NAS service — CRUD NAS dengan enkripsi shared secret.

AGENT.md rule #3: shared_secret TIDAK BOLEH disimpan plaintext di DB.
Enkripsi menggunakan Fernet (symmetric) dengan SECRET_KEY dari settings.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.models.nas_ext import NasExt
from app.models.radius_core import NasCore
from app.schemas.nas import NasCreateRequest, NasUpdateRequest

settings = get_settings()


class NasNotFoundError(Exception):
    """NAS tidak ditemukan."""


class NasNasnameConflictError(Exception):
    """NAS dengan nasname ini sudah terdaftar."""


# ---------------------------------------------------------------------------
# Enkripsi shared secret (Fernet symmetric encryption)
# ---------------------------------------------------------------------------


def _get_fernet() -> Fernet:
    """Buat instance Fernet dari SECRET_KEY settings.

    SECRET_KEY di-hash/pad ke 32 bytes agar bisa dipakai sebagai Fernet key.
    """
    import hashlib

    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_secret(plaintext: str) -> str:
    """Enkripsi shared secret sebelum disimpan ke DB.

    Args:
        plaintext: Shared secret plain text.

    Returns:
        String terenkripsi (base64url Fernet token).

    """
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Dekripsi shared secret dari DB.

    Args:
        ciphertext: Shared secret terenkripsi dari DB.

    Returns:
        Shared secret plain text.

    Raises:
        ValueError: Jika token tidak valid (korup atau key berbeda).

    """
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Gagal dekripsi shared secret NAS — token invalid") from e


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def create_nas(db: AsyncSession, data: NasCreateRequest) -> tuple[NasCore, NasExt]:
    """Buat NAS baru (NasCore + NasExt).

    Args:
        db: DB session.
        data: NasCreateRequest payload.

    Returns:
        Tuple (NasCore, NasExt).

    Raises:
        NasNasnameConflictError: Jika nasname sudah terdaftar.

    """
    # Cek duplikasi
    existing = await db.execute(select(NasCore).where(NasCore.nasname == data.nasname))
    if existing.scalar_one_or_none():
        raise NasNasnameConflictError(f"NAS '{data.nasname}' sudah terdaftar")

    # Enkripsi shared secret (AGENT.md rule #3)
    encrypted_secret = encrypt_secret(data.shared_secret)

    nas_core = NasCore(
        nasname=data.nasname,
        shortname=data.shortname,
        type=data.nas_type,
        ports=data.ports,
        secret=encrypted_secret,
        description=data.description,
    )
    db.add(nas_core)
    await db.flush()

    nas_ext = NasExt(
        nasname=data.nasname,
        vendor_profile_id=data.vendor_profile_id,
        location=data.location,
        tenant_id=data.tenant_id,
        is_active=True,
    )
    db.add(nas_ext)
    await db.flush()
    await db.refresh(nas_core)
    await db.refresh(nas_ext)

    return await get_nas(db, nas_ext.id)


async def get_nas(
    db: AsyncSession,
    nas_id: int,
    tenant_id: int | None = None,
) -> tuple[NasCore, NasExt]:
    """Ambil NAS berdasarkan ID NasExt.

    Args:
        db: DB session.
        nas_id: ID NasExt.
        tenant_id: Scope tenant (None = superadmin).

    Returns:
        Tuple (NasCore, NasExt).

    Raises:
        NasNotFoundError: Jika tidak ditemukan.

    """
    query = select(NasExt).where(NasExt.id == nas_id).options(joinedload(NasExt.vendor_profile))
    if tenant_id is not None:
        query = query.where(NasExt.tenant_id == tenant_id)

    result = await db.execute(query)
    nas_ext = result.scalar_one_or_none()
    if nas_ext is None:
        raise NasNotFoundError(f"NAS ID {nas_id} tidak ditemukan")

    core_result = await db.execute(select(NasCore).where(NasCore.nasname == nas_ext.nasname))
    nas_core = core_result.scalar_one_or_none()
    if nas_core is None:
        raise NasNotFoundError(f"NAS core untuk '{nas_ext.nasname}' tidak ditemukan")

    return nas_core, nas_ext


async def list_nas(
    db: AsyncSession,
    tenant_id: int | None = None,
) -> tuple[list[tuple[NasCore, NasExt]], int]:
    """List semua NAS yang visible untuk tenant.

    Args:
        db: DB session.
        tenant_id: Scope tenant.

    Returns:
        Tuple (list of (NasCore, NasExt) tuples, total count).

    """
    query = select(NasExt).options(joinedload(NasExt.vendor_profile))
    count_query = select(func.count()).select_from(NasExt)

    if tenant_id is not None:
        query = query.where((NasExt.tenant_id == tenant_id) | (NasExt.tenant_id.is_(None)))
        count_query = count_query.where((NasExt.tenant_id == tenant_id) | (NasExt.tenant_id.is_(None)))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.order_by(NasExt.nasname))
    ext_list = list(result.scalars().all())

    pairs: list[tuple[NasCore, NasExt]] = []
    for ext in ext_list:
        core_result = await db.execute(select(NasCore).where(NasCore.nasname == ext.nasname))
        core = core_result.scalar_one_or_none()
        if core:
            pairs.append((core, ext))

    return pairs, total


async def update_nas(
    db: AsyncSession,
    nas_id: int,
    data: NasUpdateRequest,
    tenant_id: int | None = None,
) -> tuple[NasCore, NasExt]:
    """Update NAS (partial update di NasCore dan NasExt).

    Args:
        db: DB session.
        nas_id: ID NasExt.
        data: NasUpdateRequest payload.
        tenant_id: Scope tenant.

    Returns:
        Tuple (NasCore, NasExt) yang sudah diupdate.

    Raises:
        NasNotFoundError: Jika tidak ditemukan.

    """
    nas_core, nas_ext = await get_nas(db, nas_id, tenant_id)

    if data.shortname is not None:
        nas_core.shortname = data.shortname
    if data.nas_type is not None:
        nas_core.type = data.nas_type
    if data.ports is not None:
        nas_core.ports = data.ports
    if data.description is not None:
        nas_core.description = data.description
    if data.shared_secret is not None:
        # Enkripsi secret baru (AGENT.md rule #3)
        nas_core.secret = encrypt_secret(data.shared_secret)

    if data.vendor_profile_id is not None:
        nas_ext.vendor_profile_id = data.vendor_profile_id
    if data.location is not None:
        nas_ext.location = data.location
    if data.is_active is not None:
        nas_ext.is_active = data.is_active

    await db.flush()
    await db.refresh(nas_core)
    await db.refresh(nas_ext)
    return await get_nas(db, nas_id, tenant_id)


async def delete_nas(
    db: AsyncSession,
    nas_id: int,
    tenant_id: int | None = None,
) -> None:
    """Hapus NAS (NasCore + NasExt).

    Args:
        db: DB session.
        nas_id: ID NasExt.
        tenant_id: Scope tenant.

    Raises:
        NasNotFoundError: Jika tidak ditemukan.

    """
    nas_core, nas_ext = await get_nas(db, nas_id, tenant_id)
    await db.delete(nas_ext)
    await db.delete(nas_core)
    await db.flush()
