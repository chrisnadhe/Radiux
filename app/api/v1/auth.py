"""Router autentikasi — login, logout, me."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUserId, DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.services import auth_service

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

_COOKIE_NAME = "access_token"
_COOKIE_MAX_AGE = settings.access_token_expire_minutes * 60


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login admin Radiux",
    status_code=status.HTTP_200_OK,
)
async def login(data: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """Autentikasi admin dan set JWT di cookie httponly.

    - Token disimpan sebagai cookie `access_token` (httponly, samesite=lax).
    - Response body hanya berisi info non-sensitif (username, role).

    """
    try:
        user = await auth_service.authenticate_user(db, data.username, data.password)
    except auth_service.AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e

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
        secure=not settings.debug,  # secure=True di production (HTTPS only)
    )

    return TokenResponse(message="Login berhasil", username=user.username, role=user.role.value)


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
