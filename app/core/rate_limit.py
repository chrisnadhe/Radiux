"""Custom Rate Limiting Dependency menggunakan Redis."""

import redis.asyncio as redis
from fastapi import Request, HTTPException, status
from app.core.config import get_settings

settings = get_settings()

class RateLimiter:
    """Dependency untuk Rate Limiting sederhana."""
    
    def __init__(self, times: int = 5, seconds: int = 60):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "127.0.0.1"
        # Gunakan path untuk membedakan endpoint
        key = f"rate_limit:{request.url.path}:{ip}"
        
        redis_conn = redis.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)
        try:
            current = await redis_conn.incr(key)
            if current == 1:
                await redis_conn.expire(key, self.seconds)
                
            if current > self.times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests",
                )
        finally:
            await redis_conn.close()
