"""Unit tests untuk security utilities: JWT dan password hashing."""

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_token_safe,
    get_password_hash,
    verify_password,
    verify_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test suite untuk password hashing (bcrypt)."""

    def test_hash_is_not_plaintext(self) -> None:
        """Hash tidak boleh sama dengan password asli."""
        hashed = get_password_hash("mysecretpassword")
        assert hashed != "mysecretpassword"

    def test_verify_correct_password(self) -> None:
        """verify_password harus return True untuk password yang benar."""
        hashed = get_password_hash("correct_horse_battery_staple")
        assert verify_password("correct_horse_battery_staple", hashed) is True

    def test_verify_wrong_password(self) -> None:
        """verify_password harus return False untuk password yang salah."""
        hashed = get_password_hash("correct_horse_battery_staple")
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_different_hashes(self) -> None:
        """Dua hash dari password yang sama harus berbeda (bcrypt salt)."""
        hash1 = get_password_hash("same_password")
        hash2 = get_password_hash("same_password")
        assert hash1 != hash2
        # Tapi keduanya harus bisa diverifikasi
        assert verify_password("same_password", hash1) is True
        assert verify_password("same_password", hash2) is True


@pytest.mark.unit
class TestJWT:
    """Test suite untuk JWT create & verify."""

    def test_create_and_verify_token(self) -> None:
        """Token yang dibuat harus bisa di-decode dengan benar."""
        token = create_access_token(subject=42)
        payload = verify_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"

    def test_token_with_extra_claims(self) -> None:
        """Extra claims harus ada di payload JWT."""
        token = create_access_token(
            subject=1,
            extra_claims={"role": "superadmin", "tenant_id": 99},
        )
        payload = verify_token(token)
        assert payload["role"] == "superadmin"
        assert payload["tenant_id"] == 99

    def test_invalid_token_raises(self) -> None:
        """Token yang tidak valid harus raise JWTError."""
        with pytest.raises(JWTError):
            verify_token("ini.bukan.token.yang.valid")

    def test_decode_safe_returns_none_on_invalid(self) -> None:
        """decode_token_safe harus return None untuk token invalid."""
        result = decode_token_safe("bukan_token_valid")
        assert result is None

    def test_decode_safe_returns_payload_on_valid(self) -> None:
        """decode_token_safe harus return payload untuk token valid."""
        token = create_access_token(subject=7)
        result = decode_token_safe(token)
        assert result is not None
        assert result["sub"] == "7"
