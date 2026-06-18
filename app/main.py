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
    monitoring_service,
    nas_service,
    package_service,
    report_service,
    scheduler_service,
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
    scheduler_service.start_scheduler()
    yield
    scheduler_service.stop_scheduler()


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

    scope_tenant_id = None if user.is_superadmin else user.tenant_id

    # Ambil stats dari service layer
    customers, total_customers = await customer_service.list_customers(
        db, tenant_id=scope_tenant_id, page=1, page_size=1
    )
    active_customers, active_total = await customer_service.list_customers(
        db,
        tenant_id=scope_tenant_id,
        page=1,
        page_size=1,
        status=customer_service.CustomerStatus.ACTIVE,
    )
    packages, total_packages = await package_service.list_packages(db, tenant_id=None, include_inactive=False)
    nas_pairs, total_nas = await nas_service.list_nas(db, tenant_id=scope_tenant_id)

    # Ambil sesi aktif untuk ringkasan
    active_sessions = await monitoring_service.get_active_sessions(db, tenant_id=scope_tenant_id)

    from types import SimpleNamespace

    # Ambil balance jika reseller
    wallet_balance = 0.0
    if not user.is_superadmin:
        from sqlalchemy import select

        from app.models.tenants import Tenant

        tenant_obj = await db.scalar(select(Tenant).where(Tenant.id == user.tenant_id))
        if tenant_obj:
            wallet_balance = float(tenant_obj.balance)

    stats = SimpleNamespace(
        total_customers=total_customers,
        active_customers=active_total,
        total_packages=total_packages,
        total_nas=total_nas,
        active_sessions=len(active_sessions),
        wallet_balance=wallet_balance,
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

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    customers, total = await customer_service.list_customers(db, tenant_id=scope_tenant_id, page=1, page_size=20)
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

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    pairs, _ = await nas_service.list_nas(db, tenant_id=scope_tenant_id)
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


# ---------------------------------------------------------------------------
# Page: Tenants & Resellers
# ---------------------------------------------------------------------------
@app.get("/tenants", response_class=HTMLResponse, include_in_schema=False)
async def tenants_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen tenants / resellers."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    if not user.is_superadmin:
        # Redirect reseller ke halaman dashboard jika mencoba akses ini
        return RedirectResponse(url="/", status_code=302)  # type: ignore[return-value]

    from sqlalchemy import select

    from app.models.tenants import Tenant

    result = await db.scalars(select(Tenant).where(Tenant.id != 1).order_by(Tenant.id.desc()))
    tenants = result.all()

    return templates.TemplateResponse(
        request=request,
        name="tenants/index.html",
        context=_base_ctx(request, user, active_page="tenants", tenants=tenants),
    )


# ---------------------------------------------------------------------------
# Page: Monitoring
# ---------------------------------------------------------------------------
@app.get("/monitoring", response_class=HTMLResponse, include_in_schema=False)
async def monitoring_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman live monitoring."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    return templates.TemplateResponse(
        request=request,
        name="monitoring/dashboard.html",
        context=_base_ctx(request, user, active_page="monitoring"),
    )


# ---------------------------------------------------------------------------
# Page: Vouchers
# ---------------------------------------------------------------------------
@app.get("/vouchers", response_class=HTMLResponse, include_in_schema=False)
async def vouchers_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen voucher prabayar."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from app.services import package_service, voucher_service

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    batches = await voucher_service.get_voucher_batches(db, tenant_id=scope_tenant_id or 1)
    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=False)

    return templates.TemplateResponse(
        request=request,
        name="vouchers/index.html",
        context=_base_ctx(request, user, active_page="vouchers", batches=batches, packages=packages),
    )


@app.get("/vouchers/{batch_id}/print", response_class=HTMLResponse, include_in_schema=False)
async def print_vouchers_page(
    request: Request,
    batch_id: int,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman cetak HTML voucher."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from fastapi import HTTPException

    from app.services import voucher_service

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    vouchers = await voucher_service.get_vouchers_by_batch(db, batch_id, tenant_id=scope_tenant_id or 1)
    if not vouchers:
        raise HTTPException(status_code=404, detail="Batch tidak ditemukan")

    return templates.TemplateResponse(
        request=request,
        name="vouchers/print.html",
        context=_base_ctx(request, user, active_page="vouchers", batch_id=batch_id, vouchers=vouchers),
    )


# ---------------------------------------------------------------------------
# Page: Billing & Invoices
# ---------------------------------------------------------------------------
@app.get("/billing", response_class=HTMLResponse, include_in_schema=False)
async def billing_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen tagihan pascabayar."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from app.services import billing_service, customer_service

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    invoices = await billing_service.get_invoices(db, tenant_id=scope_tenant_id or 1)

    # Ambil customer untuk dropdown manual invoice
    customers, _ = await customer_service.list_customers(db, tenant_id=scope_tenant_id, page=1, page_size=1000)

    return templates.TemplateResponse(
        request=request,
        name="billing/index.html",
        context=_base_ctx(request, user, active_page="billing", invoices=invoices, customers=customers),
    )


@app.get("/billing/{invoice_id}/print", response_class=HTMLResponse, include_in_schema=False)
async def print_invoice_page(
    invoice_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman cetak invoice."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from fastapi import HTTPException

    from app.services import billing_service

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    invoice = await billing_service.get_invoice_with_customer(db, invoice_id, tenant_id=scope_tenant_id or 1)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")

    return templates.TemplateResponse(
        request=request,
        name="billing/print.html",
        context=_base_ctx(request, user, active_page="billing", invoice=invoice),
    )


# ---------------------------------------------------------------------------
# Page: Admin Users
# ---------------------------------------------------------------------------
@app.get("/admin-users", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman manajemen Admin Users."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.models.admin_users import AdminUser

    stmt = select(AdminUser).options(joinedload(AdminUser.tenant)).order_by(AdminUser.id.desc())
    if not user.is_superadmin:
        stmt = stmt.where(AdminUser.tenant_id == user.tenant_id)

    result = await db.scalars(stmt)
    admin_users = result.all()

    # Ambil list tenant untuk dropdown form
    from app.models.tenants import Tenant

    tenants_result = await db.scalars(select(Tenant).order_by(Tenant.name))
    tenants = tenants_result.all()

    return templates.TemplateResponse(
        request=request,
        name="admin_users/index.html",
        context=_base_ctx(request, user, active_page="admin_users", admin_users=admin_users, tenants=tenants),
    )


# ---------------------------------------------------------------------------
# Page: Reports — Usage
# ---------------------------------------------------------------------------
@app.get("/reports", response_class=HTMLResponse, include_in_schema=False)
async def reports_usage_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    date_from: str | None = None,
    date_to: str | None = None,
) -> HTMLResponse:
    """Halaman laporan pemakaian."""
    from datetime import date

    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    scope_tenant_id = None if user.is_superadmin else user.tenant_id

    today = date.today()
    df = date.fromisoformat(date_from) if date_from else today.replace(day=1)
    dt = date.fromisoformat(date_to) if date_to else today

    rows = await report_service.get_usage_report(db, scope_tenant_id, df, dt)

    # Data untuk chart (top 10)
    top10 = rows[:10]
    chart_labels = [r["full_name"][:20] for r in top10]
    chart_downloads = [r["download_gb"] for r in top10]
    chart_uploads = [r["upload_gb"] for r in top10]

    total_sessions = sum(r["session_count"] for r in rows)
    total_download_gb = round(sum(r["download_gb"] for r in rows), 2)
    total_upload_gb = round(sum(r["upload_gb"] for r in rows), 2)

    return templates.TemplateResponse(
        request=request,
        name="reports/index.html",
        context=_base_ctx(
            request,
            user,
            active_page="reports",
            rows=rows,
            date_from=df.isoformat(),
            date_to=dt.isoformat(),
            total_sessions=total_sessions,
            total_download_gb=total_download_gb,
            total_upload_gb=total_upload_gb,
            chart_labels=chart_labels,
            chart_downloads=chart_downloads,
            chart_uploads=chart_uploads,
        ),
    )


# ---------------------------------------------------------------------------
# Page: Reports — Revenue
# ---------------------------------------------------------------------------
@app.get("/reports/revenue", response_class=HTMLResponse, include_in_schema=False)
async def reports_revenue_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    year: int | None = None,
    month: int | None = None,
) -> HTMLResponse:
    """Halaman laporan revenue."""
    from datetime import date

    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    scope_tenant_id = None if user.is_superadmin else user.tenant_id
    today = date.today()
    y = year or today.year
    m = month or today.month

    data = await report_service.get_revenue_report(db, scope_tenant_id, y, m)
    trend = await report_service.get_revenue_trend(db, scope_tenant_id, months=6)

    return templates.TemplateResponse(
        request=request,
        name="reports/revenue.html",
        context=_base_ctx(
            request,
            user,
            active_page="reports_revenue",
            year=y,
            month=m,
            current_year=today.year,
            period=data["period"],
            summary=data["summary"],
            invoices=data["invoices"],
            by_tenant=data["by_tenant"],
            wallet_summary=data["wallet_summary"],
            trend_labels=[t["label"] for t in trend],
            trend_invoice=[t["invoice_amount"] for t in trend],
            trend_payment=[t["payment_amount"] for t in trend],
        ),
    )


# ---------------------------------------------------------------------------
# Page: Notifications (Phase 8)
# ---------------------------------------------------------------------------
@app.get("/notifications", response_class=HTMLResponse, include_in_schema=False)
async def notifications_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Halaman riwayat notifikasi."""
    access_token = request.cookies.get("access_token")
    user = await _resolve_user(access_token, db)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)  # type: ignore[return-value]

    from app.services import notification_service

    tenant_id = None if user.is_superadmin else user.tenant_id
    notifs = await notification_service.get_notifications(db, tenant_id=tenant_id, limit=50)

    return templates.TemplateResponse(
        request=request,
        name="notifications/index.html",
        context=_base_ctx(
            request,
            user,
            active_page="notifications",
            notifications=notifs,
        ),
    )
