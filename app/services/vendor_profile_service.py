"""Vendor Profile service — CRUD + logika format rate-limit per vendor.

Fungsi ``format_rate_limit()`` mengembalikan list tuple (attribute, op, value)
yang siap diinsert ke tabel ``radgroupreply``. Setiap NasVendorProfile yang
aktif akan menghasilkan satu atau lebih entry.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nas_vendor_profiles import NasVendorProfile, RateLimitFormat
from app.schemas.vendor_profiles import VendorProfileCreate, VendorProfileUpdate


class VendorProfileNotFoundError(Exception):
    """Vendor profile tidak ditemukan."""


class VendorProfileSlugConflictError(Exception):
    """vendor_slug sudah dipakai profil lain."""


class VendorProfileBuiltinError(Exception):
    """Operasi tidak diizinkan pada profil bawaan (is_builtin=True)."""


# ---------------------------------------------------------------------------
# Logika format rate-limit
# ---------------------------------------------------------------------------


def _cisco_burst(bps: int) -> int:
    """Hitung nilai burst untuk Cisco rate-limit.

    Burst = maks(8000, bps // 8). Nilai minimum 8000 bytes untuk link lambat.

    Args:
        bps: Bandwidth dalam bits per second.

    Returns:
        Normal burst dan excess burst dalam bytes.

    """
    return max(8000, bps // 8)


def format_rate_limit(
    profile: NasVendorProfile,
    up_kbps: int,
    down_kbps: int,
) -> list[tuple[str, str, str]]:
    """Kembalikan list (attribute, op, value) untuk radgroupreply.

    Bila speed = 0 (unlimited) dan format bukan CISCO_IOS, kembalikan list
    kosong (tidak ada rate-limit di group reply).

    Args:
        profile: NasVendorProfile yang aktif.
        up_kbps: Upload speed dalam Kbps (0 = unlimited).
        down_kbps: Download speed dalam Kbps (0 = unlimited).

    Returns:
        List tuple ``(attribute_name, operator, value)`` siap untuk radgroupreply.

    """
    fmt = profile.rate_limit_format

    if fmt == RateLimitFormat.NONE or profile.rate_limit_attribute is None:
        return []

    # Jika semua speed 0 (unlimited) dan bukan Cisco, tidak perlu entry
    if fmt != RateLimitFormat.CISCO_IOS and up_kbps == 0 and down_kbps == 0:
        return []

    attr = profile.rate_limit_attribute
    entries: list[tuple[str, str, str]] = []

    if fmt == RateLimitFormat.MIKROTIK:
        up = f"{up_kbps}k" if up_kbps > 0 else "0"
        down = f"{down_kbps}k" if down_kbps > 0 else "0"
        entries.append((attr, "=", f"{down}/{up}"))

    elif fmt == RateLimitFormat.KBPS_SINGLE_DOWN:
        if down_kbps > 0:
            entries.append((attr, "=", str(down_kbps)))

    elif fmt == RateLimitFormat.KBPS_SINGLE_UP:
        if up_kbps > 0:
            entries.append((attr, "=", str(up_kbps)))

    elif fmt == RateLimitFormat.BPS_SINGLE_DOWN:
        if down_kbps > 0:
            entries.append((attr, "=", str(down_kbps * 1000)))

    elif fmt == RateLimitFormat.BPS_SINGLE_UP:
        if up_kbps > 0:
            entries.append((attr, "=", str(up_kbps * 1000)))

    elif fmt == RateLimitFormat.CISCO_IOS:
        # Cisco IOS/IOS-XE: dua Cisco-AVPair lcp:interface-config
        # rate-limit input = upload (dari perspektif NAS = traffic masuk dari pelanggan)
        # rate-limit output = download (traffic keluar ke pelanggan)
        if up_kbps > 0:
            up_bps = up_kbps * 1000
            burst = _cisco_burst(up_bps)
            entries.append(
                (
                    "Cisco-AVPair",
                    "+=",
                    f"lcp:interface-config#1=rate-limit input {up_bps} {burst} {burst} "
                    f"conform-action transmit exceed-action drop",
                )
            )
        if down_kbps > 0:
            down_bps = down_kbps * 1000
            burst = _cisco_burst(down_bps)
            entries.append(
                (
                    "Cisco-AVPair",
                    "+=",
                    f"lcp:interface-config#2=rate-limit output {down_bps} {burst} {burst} "
                    f"conform-action transmit exceed-action drop",
                )
            )

    # Proses extra_group_reply_attrs (atribut tambahan)
    if profile.extra_group_reply_attrs:
        for extra in profile.extra_group_reply_attrs:
            extra_attr: str = extra.get("attribute", "")
            extra_op: str = extra.get("op", "=")
            extra_fmt_str: str = extra.get("format", "none")
            extra_fmt = (
                RateLimitFormat(extra_fmt_str)
                if extra_fmt_str in RateLimitFormat._value2member_map_
                else RateLimitFormat.NONE
            )

            if extra_fmt == RateLimitFormat.KBPS_SINGLE_DOWN and down_kbps > 0:
                entries.append((extra_attr, extra_op, str(down_kbps)))
            elif extra_fmt == RateLimitFormat.KBPS_SINGLE_UP and up_kbps > 0:
                entries.append((extra_attr, extra_op, str(up_kbps)))
            elif extra_fmt == RateLimitFormat.BPS_SINGLE_DOWN and down_kbps > 0:
                entries.append((extra_attr, extra_op, str(down_kbps * 1000)))
            elif extra_fmt == RateLimitFormat.BPS_SINGLE_UP and up_kbps > 0:
                entries.append((extra_attr, extra_op, str(up_kbps * 1000)))

    return entries


def get_all_rate_limit_attributes(profile: NasVendorProfile) -> list[str]:
    """Kembalikan semua nama atribut yang dikelola profil ini.

    Dipakai saat cleanup entri lama di radgroupreply sebelum sync ulang.

    Args:
        profile: NasVendorProfile.

    Returns:
        List nama atribut RADIUS.

    """
    attrs: list[str] = []
    if profile.rate_limit_attribute:
        attrs.append(profile.rate_limit_attribute)
    if profile.rate_limit_format == RateLimitFormat.CISCO_IOS:
        # Cisco AVPair diidentifikasi by attribute name saja (Cisco-AVPair)
        attrs.append("Cisco-AVPair")
    if profile.extra_group_reply_attrs:
        for extra in profile.extra_group_reply_attrs:
            extra_attr: str = extra.get("attribute", "")
            if extra_attr and extra_attr not in attrs:
                attrs.append(extra_attr)
    return attrs


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------


async def list_vendor_profiles(
    db: AsyncSession,
    include_inactive: bool = False,
) -> tuple[list[NasVendorProfile], int]:
    """List semua vendor profiles.

    Args:
        db: DB session.
        include_inactive: Sertakan profil non-aktif.

    Returns:
        Tuple (list of NasVendorProfile, total count).

    """
    query = select(NasVendorProfile)
    count_query = select(func.count()).select_from(NasVendorProfile)

    if not include_inactive:
        query = query.where(NasVendorProfile.is_active.is_(True))
        count_query = count_query.where(NasVendorProfile.is_active.is_(True))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    result = await db.execute(query.order_by(NasVendorProfile.vendor_slug))
    profiles = list(result.scalars().all())

    return profiles, total


async def get_vendor_profile(db: AsyncSession, profile_id: int) -> NasVendorProfile:
    """Ambil vendor profile berdasarkan ID.

    Args:
        db: DB session.
        profile_id: ID NasVendorProfile.

    Returns:
        NasVendorProfile.

    Raises:
        VendorProfileNotFoundError: Jika tidak ditemukan.

    """
    result = await db.execute(select(NasVendorProfile).where(NasVendorProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise VendorProfileNotFoundError(f"Vendor profile ID {profile_id} tidak ditemukan")
    return profile


async def get_vendor_profile_by_slug(db: AsyncSession, slug: str) -> NasVendorProfile:
    """Ambil vendor profile berdasarkan slug.

    Args:
        db: DB session.
        slug: vendor_slug.

    Returns:
        NasVendorProfile.

    Raises:
        VendorProfileNotFoundError: Jika tidak ditemukan.

    """
    result = await db.execute(select(NasVendorProfile).where(NasVendorProfile.vendor_slug == slug))
    profile = result.scalar_one_or_none()
    if profile is None:
        raise VendorProfileNotFoundError(f"Vendor profile slug '{slug}' tidak ditemukan")
    return profile


async def get_all_active_profiles(db: AsyncSession) -> list[NasVendorProfile]:
    """Ambil semua vendor profiles yang aktif.

    Dipakai oleh package_service saat sync radgroupreply.

    Args:
        db: DB session.

    Returns:
        List NasVendorProfile yang aktif.

    """
    result = await db.execute(
        select(NasVendorProfile).where(NasVendorProfile.is_active.is_(True)).order_by(NasVendorProfile.id)
    )
    return list(result.scalars().all())


async def create_vendor_profile(
    db: AsyncSession,
    data: VendorProfileCreate,
) -> NasVendorProfile:
    """Buat custom vendor profile.

    Args:
        db: DB session.
        data: VendorProfileCreate payload.

    Returns:
        NasVendorProfile yang baru dibuat.

    Raises:
        VendorProfileSlugConflictError: Jika vendor_slug sudah dipakai.

    """
    existing = await db.execute(select(NasVendorProfile).where(NasVendorProfile.vendor_slug == data.vendor_slug))
    if existing.scalar_one_or_none():
        raise VendorProfileSlugConflictError(f"vendor_slug '{data.vendor_slug}' sudah dipakai")

    profile = NasVendorProfile(
        vendor_slug=data.vendor_slug,
        name=data.name,
        description=data.description,
        rate_limit_attribute=data.rate_limit_attribute,
        rate_limit_format=data.rate_limit_format,
        extra_group_reply_attrs=data.extra_group_reply_attrs,
        is_builtin=False,
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def update_vendor_profile(
    db: AsyncSession,
    profile_id: int,
    data: VendorProfileUpdate,
) -> NasVendorProfile:
    """Update vendor profile.

    Args:
        db: DB session.
        profile_id: ID NasVendorProfile.
        data: VendorProfileUpdate payload.

    Returns:
        NasVendorProfile yang sudah diupdate.

    Raises:
        VendorProfileNotFoundError: Jika tidak ditemukan.

    """
    profile = await get_vendor_profile(db, profile_id)

    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)
    return profile


async def delete_vendor_profile(db: AsyncSession, profile_id: int) -> None:
    """Hapus custom vendor profile (builtin tidak bisa dihapus).

    Args:
        db: DB session.
        profile_id: ID NasVendorProfile.

    Raises:
        VendorProfileNotFoundError: Jika tidak ditemukan.
        VendorProfileBuiltinError: Jika profil adalah bawaan (is_builtin=True).

    """
    profile = await get_vendor_profile(db, profile_id)
    if profile.is_builtin:
        raise VendorProfileBuiltinError(
            f"Profil bawaan '{profile.vendor_slug}' tidak bisa dihapus. "
            "Nonaktifkan dengan is_active=false jika tidak dibutuhkan."
        )
    await db.delete(profile)
    await db.flush()


async def get_active_profiles_attributes(db: AsyncSession) -> dict[str, list[str]]:
    """Kembalikan mapping vendor_slug → list attribute names dari semua profil aktif.

    Dipakai saat cleanup radgroupreply lama sebelum sync ulang.

    Args:
        db: DB session.

    Returns:
        Dict {vendor_slug: [attr1, attr2, ...]}.

    """
    profiles = await get_all_active_profiles(db)
    return {p.vendor_slug: get_all_rate_limit_attributes(p) for p in profiles}


def _get_extra_attrs_value(extra: dict[str, Any]) -> str | None:  # noqa: ANN401
    """Helper untuk extract 'attribute' dari extra_group_reply_attrs entry."""
    return extra.get("attribute")
