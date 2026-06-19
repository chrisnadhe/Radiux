"""Unit tests untuk rate_limit — custom Redis-based RateLimiter."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.rate_limit import RateLimiter


def _make_request(path: str = "/api/v1/auth/login", ip: str = "127.0.0.1") -> MagicMock:
    """Buat mock Request FastAPI."""
    request = MagicMock()
    request.url.path = path
    request.client.host = ip
    return request


def _make_redis_mock(counter_value: int) -> AsyncMock:
    """Buat mock Redis connection yang mengembalikan counter_value saat incr()."""
    redis_conn = AsyncMock()
    redis_conn.incr = AsyncMock(return_value=counter_value)
    redis_conn.expire = AsyncMock()
    redis_conn.close = AsyncMock()
    return redis_conn


@pytest.mark.unit
class TestRateLimiter:
    """Test suite untuk RateLimiter dependency."""

    async def test_first_request_passes(self) -> None:
        """Request pertama harus diteruskan (tidak raise)."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request()

        with patch("app.core.rate_limit.redis.from_url", return_value=_make_redis_mock(1)):
            # Tidak boleh raise
            await limiter(request)

    async def test_request_within_limit_passes(self) -> None:
        """Request ke-N (masih dalam batas) harus diteruskan."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request()

        with patch("app.core.rate_limit.redis.from_url", return_value=_make_redis_mock(5)):
            # Tepat di batas — tidak boleh raise
            await limiter(request)

    async def test_request_over_limit_raises_429(self) -> None:
        """Request ke-N+1 (melebihi batas) harus raise HTTPException 429."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request()

        with patch("app.core.rate_limit.redis.from_url", return_value=_make_redis_mock(6)):
            with pytest.raises(HTTPException) as exc_info:
                await limiter(request)
            assert exc_info.value.status_code == 429

    async def test_expire_called_on_first_request(self) -> None:
        """expire() harus dipanggil saat counter baru (incr() mengembalikan 1)."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request()
        mock_redis = _make_redis_mock(1)

        with patch("app.core.rate_limit.redis.from_url", return_value=mock_redis):
            await limiter(request)

        mock_redis.expire.assert_awaited_once()

    async def test_expire_not_called_on_subsequent_requests(self) -> None:
        """expire() tidak boleh dipanggil jika counter > 1 (key sudah ada TTL)."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request()
        mock_redis = _make_redis_mock(3)

        with patch("app.core.rate_limit.redis.from_url", return_value=mock_redis):
            await limiter(request)

        mock_redis.expire.assert_not_awaited()

    async def test_redis_close_always_called(self) -> None:
        """redis_conn.close() harus selalu dipanggil bahkan jika ada exception."""
        limiter = RateLimiter(times=1, seconds=60)
        request = _make_request()
        mock_redis = _make_redis_mock(999)  # Pasti over limit

        with patch("app.core.rate_limit.redis.from_url", return_value=mock_redis):
            with pytest.raises(HTTPException):
                await limiter(request)

        mock_redis.close.assert_awaited_once()

    async def test_key_includes_path_and_ip(self) -> None:
        """Key Redis harus berisi path dan IP agar bisa membedakan endpoint."""
        limiter = RateLimiter(times=5, seconds=60)
        request = _make_request(path="/api/v1/auth/login", ip="10.0.0.1")
        mock_redis = _make_redis_mock(1)

        with patch("app.core.rate_limit.redis.from_url", return_value=mock_redis):
            await limiter(request)

        # Verifikasi key mengandung path dan IP
        incr_key = mock_redis.incr.call_args[0][0]
        assert "/api/v1/auth/login" in incr_key
        assert "10.0.0.1" in incr_key

    async def test_no_client_uses_localhost(self) -> None:
        """Jika request.client adalah None, fallback ke '127.0.0.1'."""
        limiter = RateLimiter(times=5, seconds=60)
        request = MagicMock()
        request.url.path = "/api/v1/auth/login"
        request.client = None  # Tidak ada client info
        mock_redis = _make_redis_mock(1)

        with patch("app.core.rate_limit.redis.from_url", return_value=mock_redis):
            await limiter(request)

        incr_key = mock_redis.incr.call_args[0][0]
        assert "127.0.0.1" in incr_key
