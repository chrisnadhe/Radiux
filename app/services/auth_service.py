"""Auth service — autentikasi admin dan manajemen sesi."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.admin_users import AdminUser


class AuthError(Exception):
    """Exception untuk kegagalan autentikasi."""


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> AdminUser:
    """Verifikasi username + password admin Radiux.

    Args:
        db: Database session.
        username: Username atau email admin.
        password: Password plain text.

    Returns:
        AdminUser yang valid jika autentikasi berhasil.

    Raises:
        AuthError: Jika username tidak ditemukan, password salah, atau akun non-aktif.

    """
    # Coba match via username dulu, lalu email
    result = await db.execute(select(AdminUser).where((AdminUser.username == username) | (AdminUser.email == username)))
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthError("Username atau password salah")

    if not verify_password(password, user.hashed_password):
        raise AuthError("Username atau password salah")

    if not user.is_active:
        raise AuthError("Akun dinonaktifkan — hubungi administrator")

    # Update last_login_at
    user.last_login_at = datetime.now(UTC)
    await db.flush()

    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> AdminUser | None:
    """Ambil AdminUser berdasarkan ID.

    Args:
        db: Database session.
        user_id: ID user.

    Returns:
        AdminUser atau None jika tidak ditemukan.

    """
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    return result.scalar_one_or_none()


async def create_superadmin(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str | None = None,
) -> AdminUser:
    """Buat akun superadmin baru.

    Dipakai oleh CLI `radiux create-superadmin`.

    Args:
        db: Database session.
        username: Username unik.
        email: Email unik.
        password: Password plain text (akan di-hash).
        full_name: Nama lengkap (opsional).

    Returns:
        AdminUser superadmin yang baru dibuat.

    """
    from app.core.security import get_password_hash
    from app.models.admin_users import AdminRole

    user = AdminUser(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=AdminRole.SUPERADMIN,
        tenant_id=None,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
