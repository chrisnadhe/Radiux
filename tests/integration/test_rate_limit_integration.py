"""Integration tests untuk Rate Limiter — ke Redis sungguhan."""

import pytest
from httpx import AsyncClient

from app.core.config import get_settings

settings = get_settings()


@pytest.mark.integration
class TestRateLimitIntegration:
    """Test Rate Limiter menggunakan Redis dari docker-compose."""

    async def test_rate_limit_with_real_redis(self, int_client: AsyncClient) -> None:
        """Kirim request melebihi batas ke satu endpoint, pastikan dapat 429."""
        # Bersihkan key redis untuk test ini dulu (opsional, karena IP beda-beda)
        import redis.asyncio as redis

        redis_conn = redis.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)
        # Hapus semua keys yang mengandung rate_limit untuk localhost
        keys = await redis_conn.keys("rate_limit:*/api/v1/auth/login*")
        if keys:
            await redis_conn.delete(*keys)
        await redis_conn.aclose()

        # Konfigurasi di RateLimiter adalah (times=5, seconds=60)
        # Kita panggil login dengan kredensial salah sebanyak 5 kali (harus 401)
        for _ in range(5):
            resp = await int_client.post(
                "/api/v1/auth/login",
                json={"username": "wronguser", "password": "wrongpass"},
            )
            # Selama masih di bawah limit, dapat 401 (karena user salah)
            assert resp.status_code == 401

        # Request ke-6 harusnya kena rate limit (429)
        resp_6 = await int_client.post(
            "/api/v1/auth/login",
            json={"username": "wronguser", "password": "wrongpass"},
        )
        assert resp_6.status_code == 429
        assert "Too Many Requests" in resp_6.json().get("detail", "")
