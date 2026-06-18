"""FastAPI dependencies yang dipakai di seluruh router."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError

from app.core.database import AsyncSession, get_db
from app.core.security import verify_token
from app.models.admin_users import AdminRole, AdminUser

# ---------------------------------------------------------------------------
# Type aliases — dipakai di seluruh codebase agar DRY
# ---------------------------------------------------------------------------
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------
async def get_current_user_id(
    access_token: Annotated[str | None, Cookie()] = None,
) -> int:
    """Extract user ID dari JWT access token di cookie.

    Raises:
        HTTPException 401: Jika token tidak ada atau invalid.

    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesi tidak valid atau sudah expired. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if access_token is None:
        raise credentials_exception

    try:
        payload = verify_token(access_token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        return int(user_id_str)
    except (JWTError, ValueError) as exc:
        raise credentials_exception from exc


async def get_current_user(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: DbSession,
) -> AdminUser:
    """Return AdminUser yang sedang login (divalidasi dari DB).

    Raises:
        HTTPException 401: Jika user tidak ditemukan atau tidak aktif.

    """
    from sqlalchemy import select

    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak valid — akun tidak ditemukan atau dinonaktifkan",
        )
    return user


async def require_superadmin(
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> AdminUser:
    """Dependency yang memastikan user adalah superadmin.

    Raises:
        HTTPException 403: Jika bukan superadmin.

    """
    if user.role != AdminRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aksi ini memerlukan hak akses superadmin",
        )
    return user


# ---------------------------------------------------------------------------
# Type aliases untuk dependency injection
# ---------------------------------------------------------------------------
CurrentUserId = Annotated[int, Depends(get_current_user_id)]
CurrentUser = Annotated[AdminUser, Depends(get_current_user)]
SuperAdminUser = Annotated[AdminUser, Depends(require_superadmin)]
