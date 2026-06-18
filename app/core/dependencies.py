"""FastAPI dependencies yang dipakai di seluruh router."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError

from app.core.database import AsyncSession, get_db
from app.core.security import verify_token

# ---------------------------------------------------------------------------
# Type aliases — dipakai di seluruh codebase agar DRY
# ---------------------------------------------------------------------------
DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------------------------------------------------------------------------
# Auth dependencies (skeleton — akan dilengkapi di Phase 1 saat model
# AdminUser sudah ada di database)
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


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
