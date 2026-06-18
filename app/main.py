"""Entrypoint aplikasi Radiux — FastAPI app factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown events
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ARG001
    """Jalankan inisialisasi saat startup dan cleanup saat shutdown."""
    # Startup
    # - Phase 1+: verifikasi koneksi DB
    # - Phase 4+: inisialisasi pyrad RADIUS client pool
    # - Phase 5+: start APScheduler
    yield
    # Shutdown
    # - Phase 5+: stop APScheduler
    # - Phase 4+: tutup koneksi RADIUS client


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    # Nonaktifkan docs di production (bisa diaktifkan kembali via env jika perlu)
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# ---------------------------------------------------------------------------
# Static files & Templates
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_v1_router)


# ---------------------------------------------------------------------------
# Root & Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health_check() -> dict[str, str]:
    """Health check endpoint untuk liveness probe Docker / load balancer.

    Returns:
        JSON dengan status ``ok`` dan versi aplikasi.

    """
    return {"status": "ok", "version": settings.app_version}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request) -> HTMLResponse:
    """Halaman utama — redirect ke dashboard atau halaman login."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
        },
    )
