"""HTML routes untuk Web UI Radiux.

Endpoint ini melayani halaman HTML lengkap dan HTMX partials.
Data diambil langsung dari service layer (bukan proxy ke API JSON)
sehingga rendering dilakukan di server dan dikirim sebagai HTML.

Auth: cek cookie `access_token`. Jika invalid → redirect ke /login.
"""

import math
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError

from app.core.config import get_settings
from app.core.database import AsyncSession, get_db
from app.core.security import verify_token
from app.models.admin_users import AdminUser
from app.models.customers import CustomerStatus
from app.services import (
    customer_service,
    nas_service,
    package_service,
    vendor_profile_service,
)

settings = get_settings()
router = APIRouter(prefix="/ui", tags=["UI"])
templates = Jinja2Templates(directory="app/templates")

# Page routes (top-level, tidak pakai prefix /ui) didaftarkan
# langsung di app/main.py agar URL bersih: /, /login, /customers, dst.


# ---------------------------------------------------------------------------
# Helper: auth check untuk UI routes
# ---------------------------------------------------------------------------


async def _get_ui_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> AdminUser | None:
    """Decode token dari cookie. Return None jika invalid (tidak raise)."""
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


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=302)


def _base_ctx(request: Request, user: AdminUser | None, **extra: object) -> dict:
    """Context dasar yang selalu disertakan di setiap template."""
    return {
        "request": request,
        "current_user": user,
        "app_version": settings.app_version,
        **extra,
    }


# ---------------------------------------------------------------------------
# Confirm dialog partial
# ---------------------------------------------------------------------------


@router.get("/confirm", response_class=HTMLResponse, include_in_schema=False)
async def confirm_dialog(
    request: Request,
    title: str = "Konfirmasi Hapus",
    message: str = "Apakah kamu yakin?",
    action_url: str = "",
    method: str = "delete",
    target: str = "#table-container",
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="partials/_confirm_dialog.html",
        context={
            "request": request,
            "title": title,
            "message": message,
            "action_url": action_url,
            "method": method,
            "target": target,
        },
    )


# ---------------------------------------------------------------------------
# Component: Audit Table
# ---------------------------------------------------------------------------
@router.get("/audit/table", response_class=HTMLResponse, include_in_schema=False)
async def audit_table(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = Query(None),
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await _get_ui_user(access_token, db)
    if not user or not user.is_superadmin:
        return HTMLResponse("<tr><td colspan='6'>Unauthorized</td></tr>")

    from sqlalchemy import desc, func, select

    from app.models.audit_logs import AuditLog

    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    stmt = stmt.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    logs = (await db.scalars(stmt)).all()

    pages = math.ceil(total / page_size) if total else 0

    return templates.TemplateResponse(
        request=request,
        name="audit/table.html",
        context=_base_ctx(request, user, logs=logs, total=total, page=page, page_size=page_size, pages=pages),
    )


# ---------------------------------------------------------------------------
# Component: Customers Table
# ---------------------------------------------------------------------------


@router.get("/customers/table", response_class=HTMLResponse, include_in_schema=False)
async def customers_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None, alias="status_filter"),
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    status_enum = CustomerStatus(status) if status else None
    customers, total = await customer_service.list_customers(
        db, tenant_id=None, page=page, page_size=page_size, search=search, status=status_enum
    )
    pages = math.ceil(total / page_size) if total else 0
    return templates.TemplateResponse(
        request=request,
        name="customers/_table.html",
        context={
            "request": request,
            "customers": customers,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
            "search": search or "",
            "status_filter": status or "",
            "current_user": user,
        },
    )


@router.get("/customers/form", response_class=HTMLResponse, include_in_schema=False)
async def customer_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=False)
    return templates.TemplateResponse(
        request=request,
        name="customers/_modal_form.html",
        context={"request": request, "customer": None, "packages": packages, "current_user": user},
    )


@router.get("/customers/{customer_id}/form", response_class=HTMLResponse, include_in_schema=False)
async def customer_form_edit(
    customer_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    try:
        customer = await customer_service.get_customer(db, customer_id, tenant_id=None)
    except customer_service.CustomerNotFoundError:
        return HTMLResponse("<p class='text-red-400 p-4'>Customer tidak ditemukan</p>", status_code=404)
    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=False)
    return templates.TemplateResponse(
        request=request,
        name="customers/_modal_form.html",
        context={"request": request, "customer": customer, "packages": packages, "current_user": user},
    )


# ---------------------------------------------------------------------------
# Packages HTMX partials
# ---------------------------------------------------------------------------


@router.get("/packages/table", response_class=HTMLResponse, include_in_schema=False)
async def packages_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
    include_inactive: bool = Query(False),
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    packages, _ = await package_service.list_packages(db, tenant_id=None, include_inactive=include_inactive)
    return templates.TemplateResponse(
        request=request,
        name="packages/_table.html",
        context={"request": request, "packages": packages, "current_user": user},
    )


@router.get("/packages/form", response_class=HTMLResponse, include_in_schema=False)
async def package_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    return templates.TemplateResponse(
        request=request,
        name="packages/_modal_form.html",
        context={"request": request, "package": None, "current_user": user},
    )


@router.get("/packages/{package_id}/form", response_class=HTMLResponse, include_in_schema=False)
async def package_form_edit(
    package_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    try:
        package = await package_service.get_package(db, package_id)
    except package_service.PackageNotFoundError:
        return HTMLResponse("<p class='text-red-400 p-4'>Paket tidak ditemukan</p>", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="packages/_modal_form.html",
        context={"request": request, "package": package, "current_user": user},
    )


# ---------------------------------------------------------------------------
# NAS HTMX partials
# ---------------------------------------------------------------------------


@router.get("/nas/table", response_class=HTMLResponse, include_in_schema=False)
async def nas_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    pairs, _ = await nas_service.list_nas(db, tenant_id=None)
    nas_list = [_build_nas_ctx(core, ext) for core, ext in pairs]
    return templates.TemplateResponse(
        request=request,
        name="nas/_table.html",
        context={"request": request, "nas_list": nas_list, "current_user": user},
    )


@router.get("/nas/form", response_class=HTMLResponse, include_in_schema=False)
async def nas_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    vendor_profiles, _ = await vendor_profile_service.list_vendor_profiles(db, include_inactive=False)
    return templates.TemplateResponse(
        request=request,
        name="nas/_modal_form.html",
        context={"request": request, "nas": None, "vendor_profiles": vendor_profiles, "current_user": user},
    )


@router.get("/nas/{nas_id}/form", response_class=HTMLResponse, include_in_schema=False)
async def nas_form_edit(
    nas_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    try:
        nas_core, nas_ext = await nas_service.get_nas(db, nas_id)
    except nas_service.NasNotFoundError:
        return HTMLResponse("<p class='text-red-400 p-4'>NAS tidak ditemukan</p>", status_code=404)
    vendor_profiles, _ = await vendor_profile_service.list_vendor_profiles(db, include_inactive=False)
    nas_ctx = _build_nas_ctx(nas_core, nas_ext)
    return templates.TemplateResponse(
        request=request,
        name="nas/_modal_form.html",
        context={"request": request, "nas": nas_ctx, "vendor_profiles": vendor_profiles, "current_user": user},
    )


def _build_nas_ctx(nas_core: object, nas_ext: object) -> object:  # type: ignore[return]
    """Simple namespace untuk pass ke template."""
    from types import SimpleNamespace

    from app.schemas.vendor_profiles import VendorProfileRead

    vp = None
    if nas_ext.vendor_profile is not None:  # type: ignore[union-attr]
        vp = VendorProfileRead.model_validate(nas_ext.vendor_profile)  # type: ignore[union-attr]
    return SimpleNamespace(
        id=nas_ext.id,  # type: ignore[union-attr]
        nasname=nas_ext.nasname,  # type: ignore[union-attr]
        shortname=getattr(nas_core, "shortname", ""),
        nas_type=getattr(nas_core, "type", "other"),
        description=getattr(nas_core, "description", None),
        vendor_profile_id=nas_ext.vendor_profile_id,  # type: ignore[union-attr]
        vendor_profile=vp,
        location=nas_ext.location,  # type: ignore[union-attr]
        is_active=nas_ext.is_active,  # type: ignore[union-attr]
    )


# ---------------------------------------------------------------------------
# Vendor Profiles HTMX partials
# ---------------------------------------------------------------------------


@router.get("/vendor-profiles/table", response_class=HTMLResponse, include_in_schema=False)
async def vendor_profiles_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    profiles, _ = await vendor_profile_service.list_vendor_profiles(db, include_inactive=True)
    return templates.TemplateResponse(
        request=request,
        name="vendor_profiles/_table.html",
        context={"request": request, "profiles": profiles, "current_user": user},
    )


@router.get("/vendor-profiles/form", response_class=HTMLResponse, include_in_schema=False)
async def vendor_profile_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    return templates.TemplateResponse(
        request=request,
        name="vendor_profiles/_modal_form.html",
        context={"request": request, "profile": None, "current_user": user},
    )


@router.get("/vendor-profiles/{profile_id}/form", response_class=HTMLResponse, include_in_schema=False)
async def vendor_profile_form_edit(
    profile_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    try:
        profile = await vendor_profile_service.get_vendor_profile(db, profile_id)
    except vendor_profile_service.VendorProfileNotFoundError:
        return HTMLResponse("<p class='text-red-400 p-4'>Profile tidak ditemukan</p>", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="vendor_profiles/_modal_form.html",
        context={"request": request, "profile": profile, "current_user": user},
    )


# ---------------------------------------------------------------------------
# Tenants HTMX partials
# ---------------------------------------------------------------------------


@router.get("/tenants/table", response_class=HTMLResponse, include_in_schema=False)
async def tenants_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user or not user.is_superadmin:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select

    from app.models.tenants import Tenant

    result = await db.scalars(select(Tenant).where(Tenant.id != 1).order_by(Tenant.id.desc()))
    tenants = result.all()

    return templates.TemplateResponse(
        request=request,
        name="tenants/_table.html",
        context={"request": request, "tenants": tenants, "current_user": user},
    )


@router.get("/tenants/form", response_class=HTMLResponse, include_in_schema=False)
async def tenant_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user or not user.is_superadmin:
        return HTMLResponse("", status_code=403)

    return templates.TemplateResponse(
        request=request,
        name="tenants/_modal_form.html",
        context={"request": request, "tenant": None, "current_user": user},
    )


@router.get("/tenants/{tenant_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def tenant_form_edit(
    tenant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user or not user.is_superadmin:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select

    from app.models.tenants import Tenant
    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        return HTMLResponse("Tenant not found", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="tenants/_modal_form.html",
        context={"request": request, "tenant": tenant, "current_user": user},
    )


@router.get("/tenants/{tenant_id}/topup", response_class=HTMLResponse, include_in_schema=False)
async def tenant_form_topup(
    tenant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user or not user.is_superadmin:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select

    from app.models.tenants import Tenant

    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        return HTMLResponse("<p>Tenant tidak ditemukan</p>", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="tenants/_modal_topup.html",
        context={"request": request, "tenant": tenant, "current_user": user},
    )


# ---------------------------------------------------------------------------
# Admin Users HTMX partials
# ---------------------------------------------------------------------------


@router.get("/admin-users/table", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_table(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    from app.models.admin_users import AdminUser

    stmt = select(AdminUser).options(joinedload(AdminUser.tenant)).order_by(AdminUser.id.desc())
    if not user.is_superadmin:
        stmt = stmt.where(AdminUser.tenant_id == user.tenant_id)

    result = await db.scalars(stmt)
    admin_users = result.all()

    return templates.TemplateResponse(
        request=request,
        name="admin_users/_table.html",
        context={"request": request, "admin_users": admin_users, "current_user": user},
    )


@router.get("/admin-users/form", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_form_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select

    from app.models.tenants import Tenant

    tenants_result = await db.scalars(select(Tenant).order_by(Tenant.name))
    tenants = tenants_result.all()

    return templates.TemplateResponse(
        request=request,
        name="admin_users/_modal_form.html",
        context={"request": request, "admin_user": None, "tenants": tenants, "current_user": user},
    )


@router.get("/admin-users/{user_id}/form", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_form_edit(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    access_token: Annotated[str | None, Cookie()] = None,
) -> HTMLResponse:
    user = await _get_ui_user(access_token, db)
    if not user:
        return HTMLResponse("", status_code=403)

    from sqlalchemy import select

    from app.models.admin_users import AdminUser

    stmt = select(AdminUser).where(AdminUser.id == user_id)
    if not user.is_superadmin:
        stmt = stmt.where(AdminUser.tenant_id == user.tenant_id)

    admin_user = await db.scalar(stmt)
    if not admin_user:
        return HTMLResponse("<p>User tidak ditemukan</p>", status_code=404)

    from app.models.tenants import Tenant

    tenants_result = await db.scalars(select(Tenant).order_by(Tenant.name))
    tenants = tenants_result.all()

    return templates.TemplateResponse(
        request=request,
        name="admin_users/_modal_form.html",
        context={"request": request, "admin_user": admin_user, "tenants": tenants, "current_user": user},
    )
