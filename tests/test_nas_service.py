"""Unit tests untuk nas_service — enkripsi/dekripsi shared secret."""

import pytest

from app.services.nas_service import decrypt_secret, encrypt_secret


@pytest.mark.unit
class TestNasSecretEncryption:
    """Test suite enkripsi/dekripsi shared secret NAS."""

    def test_encrypt_is_not_plaintext(self) -> None:
        """Hasil enkripsi tidak boleh sama dengan plaintext."""
        secret = "radiusSuperSecret123"
        ciphertext = encrypt_secret(secret)
        assert ciphertext != secret

    def test_decrypt_returns_original(self) -> None:
        """Dekripsi harus mengembalikan nilai plaintext asli."""
        secret = "radiusSuperSecret123"
        ciphertext = encrypt_secret(secret)
        assert decrypt_secret(ciphertext) == secret

    def test_same_plaintext_different_ciphertext(self) -> None:
        """Enkripsi dua kali untuk plaintext yang sama menghasilkan ciphertext berbeda (Fernet nonce)."""
        secret = "sameSecret"
        cipher1 = encrypt_secret(secret)
        cipher2 = encrypt_secret(secret)
        assert cipher1 != cipher2
        # Keduanya harus bisa di-dekripsi ke nilai yang sama
        assert decrypt_secret(cipher1) == secret
        assert decrypt_secret(cipher2) == secret

    def test_decrypt_invalid_token_raises(self) -> None:
        """Dekripsi token invalid harus raise ValueError."""
        with pytest.raises(ValueError, match="Gagal dekripsi"):
            decrypt_secret("ini-bukan-fernet-token-valid")

    def test_encrypt_empty_string(self) -> None:
        """Enkripsi string kosong harus tetap berhasil dan bisa di-dekripsi."""
        ciphertext = encrypt_secret("")
        assert decrypt_secret(ciphertext) == ""

    def test_encrypt_special_characters(self) -> None:
        """Enkripsi karakter khusus harus berhasil."""
        secret = "s3cr3t!@#$%^&*()_+-=[]{}|;':\",./<>?"
        ciphertext = encrypt_secret(secret)
        assert decrypt_secret(ciphertext) == secret
