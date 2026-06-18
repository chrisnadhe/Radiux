"""Pydantic schemas untuk autentikasi — request/response login."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload login admin Radiux."""

    username: str = Field(..., min_length=3, max_length=64, description="Username atau email")
    password: str = Field(..., min_length=6, max_length=128)


class TokenResponse(BaseModel):
    """Response sukses login — hanya informasi non-sensitif."""

    message: str = "Login berhasil"
    username: str
    role: str
    requires_otp: bool = False


class OtpVerifyRequest(BaseModel):
    """Payload verifikasi OTP."""

    username: str = Field(..., min_length=3, max_length=64)
    otp: str = Field(..., min_length=6, max_length=6)


class MeResponse(BaseModel):
    """Info user yang sedang login."""

    id: int
    username: str
    email: str
    full_name: str | None
    role: str
    tenant_id: int | None
    is_superadmin: bool
