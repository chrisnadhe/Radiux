"""Entrypoint aplikasi Radiux — FastAPI app factory."""

import math
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.database import AsyncSession, get_db
from app.core.security import verify_token
from app.models.admin_users import AdminUser
from app.services import (
    customer_service,
    nas_service,
    package_service,
    vendor_profile_service,
)
from app.ui.routes import router as ui_router

settings = get_settings()


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown events
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ARG001
    """Jalankan inisialisasi saat startup dan cleanup saat shutdown."""
    yield


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
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
app.include_router(ui_router)


# ---------------------------------------------------------------------------
# UI Auth helper
# ---------------------------------------------------------------------------
async def _get_ui_user(
    access_token: Annotated[str | None, None] = None,
    db: AsyncSession = None,  # type: ignore[assignment]
) -> AdminUser | None:
    """Shared helper — implemented inline in page routes below."""
    ...


async def _resolve_user(
    access_token: str | None,
    db: AsyncSession,
) -> AdminUser | None:
    if access_token is None:
        return None
    try:
        payload = verify_token(access_token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        from sqlalchemy import select

        result = await db.execute(select(AdminUser).where(AdminUser.id == int(user_id_str)))
        user = result.scalar_one_or_none()
        return user if (user and user.is_active) else None
    except (JWTError, ValueError):
        return None


def _base_ctx(request: Request, user: AdminUser | None, **extra: object) -> dict:
    return {
        "request": request,
        "current_user": user,
        "app_version": settings.app_version,
        **extra,
    }


# ---------------------------------------------------------------------------
# Health check (JSON)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health_check() -> dict[str, str]:
    """Health check endpoint untuk liveness probe Docker / load balancer."""
    return {"status": "ok", "version": settings.app_version}


# ---------------------------------------------------------------------------
# Page: Login
# ---------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request) -> HTMLResponse:
    """Halaman login."""
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request, "app_version": settings.app_version},
    )


# ---------------------------------------------------------------------------
# Logout redirect (clear cookie + redirect ke /login)
# ---------------------------------------------------------------------------
@app.get("/logout-redirect", include_in_schema=False)
async def logout_redirect() -> RedirectResponse:
    """Hapus cookie dan redirect ke halaman login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token", samesite="lax")
    return response


# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Dashboard utama."""

    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    # Ambil stats dari service layer
    customers, total_customers = await customer_service.list_customers(db, tenant_id=None, page=1, page_size=1)
    active_customers, active_total = await customer_service.list_customers(
        db,
        tenant_id=None,
        page=1,
        page_size=1,
        status=customer_service.CustomerStatus.ACTIVE,
    )
    packages, total_packages = await package_service.list_packages(db, tenant_id=None, include_inactive=False)
    nas_pairs, total_nas = await nas_service.list_nas(db, tenant_id=None)

    from types import SimpleNamespace

    stats = SimpleNamespace(
        total_customers=total_customers,
        active_customers=active_total,
        total_packages=total_packages,
        total_nas=total_nas,
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context=_base_ctx(request, user, active_page="dashboard", stats=stats),
    )


# ---------------------------------------------------------------------------
# Page: Customers
# ---------------------------------------------------------------------------
@app.get("/customers", response_class=HTMLResponse, include_in_schema=False)
async def customers_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen customers."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    customers, total = await customer_service.list_customers(db, tenant_id=None, page=1, page_size=20)
    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=False)
    pages = math.ceil(total / 20) if total else 0

    return templates.TemplateResponse(
        request=request,
        name="customers/index.html",
        context=_base_ctx(
            request,
            user,
            active_page="customers",
            customers=customers,
            total=total,
            page=1,
            page_size=20,
            pages=pages,
            packages=packages,
            search="",
            status_filter="",
        ),
    )


# ---------------------------------------------------------------------------
# Page: Packages
# ---------------------------------------------------------------------------
@app.get("/packages", response_class=HTMLResponse, include_in_schema=False)
async def packages_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen paket layanan."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=False)

    return templates.TemplateResponse(
        request=request,
        name="packages/index.html",
        context=_base_ctx(request, user, active_page="packages", packages=packages),
    )


# ---------------------------------------------------------------------------
# Page: NAS Management
# ---------------------------------------------------------------------------
@app.get("/nas", response_class=HTMLResponse, include_in_schema=False)
async def nas_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen NAS devices."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    pairs, _ = await nas_service.list_nas(db, tenant_id=None)
    from app.ui.routes import _build_nas_ctx

    nas_list = [_build_nas_ctx(core, ext) for core, ext in pairs]

    return templates.TemplateResponse(
        request=request,
        name="nas/index.html",
        context=_base_ctx(request, user, active_page="nas", nas_list=nas_list),
    )


# ---------------------------------------------------------------------------
# Page: Vendor Profiles
# ---------------------------------------------------------------------------
@app.get("/vendor-profiles", response_class=HTMLResponse, include_in_schema=False)
async def vendor_profiles_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman vendor profiles."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    profiles, _ = await vendor_profile_service.list_vendor_profiles(db, include_inactive=True)

    return templates.TemplateResponse(
        request=request,
        name="vendor_profiles/index.html",
        context=_base_ctx(request, user, active_page="vendor_profiles", profiles=profiles),
    )
