"""Unit tests untuk auth_service — autentikasi dan lookup user."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.auth_service import AuthError, authenticate_user, get_user_by_id


def _make_user(
    *,
    is_active: bool = True,
    hashed_password: str = "",
) -> MagicMock:
    """Buat mock AdminUser."""
    user = MagicMock()
    user.is_active = is_active
    user.hashed_password = hashed_password
    user.last_login_at = None
    return user


def _make_db(user_or_none: object = None) -> AsyncMock:
    """Buat mock AsyncSession yang mengembalikan user saat execute."""
    db = AsyncMock()
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = user_or_none
    db.execute = AsyncMock(return_value=scalar_result)
    db.flush = AsyncMock()
    return db


@pytest.mark.unit
class TestAuthenticateUser:
    """Test suite untuk auth_service.authenticate_user()."""

    async def test_returns_user_on_correct_credentials(self) -> None:
        """Harus mengembalikan user jika username + password benar."""
        from app.core.security import get_password_hash

        hashed = get_password_hash("correctpassword")
        user = _make_user(hashed_password=hashed)
        db = _make_db(user)

        result = await authenticate_user(db, "admin", "correctpassword")
        assert result is user

    async def test_raises_when_user_not_found(self) -> None:
        """Harus raise AuthError jika user tidak ditemukan."""
        db = _make_db(user_or_none=None)

        with pytest.raises(AuthError, match="Username atau password salah"):
            await authenticate_user(db, "nonexistent", "anypassword")

    async def test_raises_on_wrong_password(self) -> None:
        """Harus raise AuthError jika password salah."""
        from app.core.security import get_password_hash

        hashed = get_password_hash("correctpassword")
        user = _make_user(hashed_password=hashed)
        db = _make_db(user)

        with pytest.raises(AuthError, match="Username atau password salah"):
            await authenticate_user(db, "admin", "wrongpassword")

    async def test_raises_when_user_inactive(self) -> None:
        """Harus raise AuthError jika user tidak aktif."""
        from app.core.security import get_password_hash

        hashed = get_password_hash("password")
        user = _make_user(is_active=False, hashed_password=hashed)
        db = _make_db(user)

        with pytest.raises(AuthError, match="Akun dinonaktifkan"):
            await authenticate_user(db, "inactive_admin", "password")

    async def test_updates_last_login_at(self) -> None:
        """Harus meng-update last_login_at setelah login sukses."""
        from app.core.security import get_password_hash

        hashed = get_password_hash("password")
        user = _make_user(hashed_password=hashed)
        db = _make_db(user)

        await authenticate_user(db, "admin", "password")
        assert user.last_login_at is not None
        db.flush.assert_awaited_once()


@pytest.mark.unit
class TestGetUserById:
    """Test suite untuk auth_service.get_user_by_id()."""

    async def test_returns_user_when_found(self) -> None:
        """Harus mengembalikan user jika ID ditemukan."""
        user = _make_user()
        db = _make_db(user)

        result = await get_user_by_id(db, 1)
        assert result is user

    async def test_returns_none_when_not_found(self) -> None:
        """Harus mengembalikan None jika ID tidak ada."""
        db = _make_db(user_or_none=None)

        result = await get_user_by_id(db, 9999)
        assert result is None
