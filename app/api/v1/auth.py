"""Router autentikasi — login, logout, me."""

import secrets
import string
from datetime import timedelta

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUserId, DbSession
from app.core.rate_limit import RateLimiter
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, MeResponse, OtpVerifyRequest, TokenResponse
from app.services import audit_service, auth_service
from app.services.notification_service import _send_via_telegram

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = settings.access_token_expire_minutes * 60


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login admin Radiux",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(data: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """Autentikasi admin dan set JWT di cookie httponly.

    - Jika 2FA aktif, kembalikan requires_otp=True dan kirim OTP via Telegram.
    - Jika tidak, Token disimpan sebagai cookie `access_token` (httponly, samesite=lax).
    """
    try:
        user = await auth_service.authenticate_user(db, data.username, data.password)
    except auth_service.AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

    if user.is_2fa_enabled:
        if not user.telegram_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA aktif tetapi Telegram Chat ID belum disetel.",
            )

        # Generate OTP
        otp = "".join(secrets.choice(string.digits) for _ in range(6))

        # Simpan OTP di Redis (5 menit)
        redis_conn = redis.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)
        await redis_conn.setex(f"otp:{user.username}", 300, otp)
        await redis_conn.close()

        # Kirim via Telegram
        msg = (
            f"🔒 <b>Kode OTP Radiux</b>\n\n"
            f"Login attempt for <code>{user.username}</code>.\n"
            f"Kode OTP Anda: <b>{otp}</b>\n\n"
            f"<i>Berlaku 5 menit.</i>"
        )
        await _send_via_telegram(settings.telegram_bot_token, user.telegram_chat_id, msg)

        await audit_service.log_action(db, "LOGIN_OTP_SENT", user.id, "admin_users", user.id)

        return TokenResponse(message="OTP Terkirim", username=user.username, role=user.role.value, requires_otp=True)

    # Generate JWT
    token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims={"role": user.role.value, "tenant_id": user.tenant_id},
    )

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
    )

    await audit_service.log_action(db, "LOGIN_SUCCESS", user.id, "admin_users", user.id)

    return TokenResponse(message="Login berhasil", username=user.username, role=user.role.value, requires_otp=False)


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verifikasi OTP admin",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def verify_otp(data: OtpVerifyRequest, response: Response, db: DbSession) -> TokenResponse:
    """Verifikasi OTP dan set JWT di cookie."""
    redis_conn = redis.from_url(str(settings.redis_url), encoding="utf-8", decode_responses=True)
    saved_otp = await redis_conn.get(f"otp:{data.username}")

    if not saved_otp or saved_otp != data.otp:
        await redis_conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP tidak valid atau sudah kedaluwarsa.",
        )

    await redis_conn.delete(f"otp:{data.username}")
    await redis_conn.close()

    # Dapatkan user info
    from sqlalchemy import select

    from app.models.admin_users import AdminUser

    user = await db.scalar(select(AdminUser).where(AdminUser.username == data.username))

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User tidak ditemukan atau dinonaktifkan.",
        )

    # Generate JWT
    token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims={"role": user.role.value, "tenant_id": user.tenant_id},
    )

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=not settings.debug,
    )

    await audit_service.log_action(db, "LOGIN_SUCCESS_2FA", user.id, "admin_users", user.id)

    return TokenResponse(message="Login berhasil", username=user.username, role=user.role.value, requires_otp=False)


@router.post(
    "/logout",
    summary="Logout dan hapus cookie sesi",
    status_code=status.HTTP_200_OK,
)
async def logout(response: Response) -> dict[str, str]:
    """Hapus cookie access_token — invalidate sesi client-side."""
    response.delete_cookie(key=_COOKIE_NAME, samesite="lax")
    return {"message": "Logout berhasil"}


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Info user yang sedang login",
)
async def get_me(user_id: CurrentUserId, db: DbSession) -> MeResponse:
    """Return informasi akun admin yang sedang login."""
    user = await auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak valid — user tidak ditemukan",
        )
    return MeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        tenant_id=user.tenant_id,
        is_superadmin=user.is_superadmin,
    )
