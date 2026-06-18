"""Fungsi keamanan: hashing password, JWT create & verify."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Return bcrypt hash dari password plain-text."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password plain-text terhadap hash yang tersimpan."""
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(
    subject: int | str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Buat JWT access token.

    Args:
        subject: Identitas principal (biasanya user ID atau username).
        expires_delta: Override durasi expiry. Default dari settings.
        extra_claims: Klaim tambahan yang dimasukkan ke payload JWT
                      (contoh: ``{"role": "superadmin", "tenant_id": 1}``).

    Returns:
        JWT string yang sudah di-sign.

    """
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> dict[str, Any]:
    """Decode dan verifikasi JWT.

    Args:
        token: JWT string.

    Returns:
        Payload dict jika valid.

    Raises:
        JWTError: Jika token invalid atau expired.

    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def decode_token_safe(token: str) -> dict[str, Any] | None:
    """Seperti ``verify_token`` tapi return ``None`` alih-alih raise jika invalid."""
    try:
        return verify_token(token)
    except JWTError:
        return None
