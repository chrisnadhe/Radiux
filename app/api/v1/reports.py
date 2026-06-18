"""API Endpoints untuk Reporting & Dashboard Analytics (Phase 7)."""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _scope(user: Any) -> int | None:  # noqa: ANN401
    """Superadmin mendapat akses semua tenant; reseller hanya tenant sendiri."""
    return None if user.is_superadmin else user.tenant_id


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------


@router.get("/summary")
async def get_summary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Stats ringkasan untuk dashboard (revenue bulan ini, invoice unpaid, customer aktif)."""
    return await report_service.get_dashboard_summary(db, tenant_id=_scope(current_user))


# ---------------------------------------------------------------------------
# Usage Report
# ---------------------------------------------------------------------------


@router.get("/usage")
async def get_usage(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    date_from: date = Query(default_factory=lambda: date.today().replace(day=1)),
    date_to: date = Query(default_factory=date.today),
) -> list[dict[str, Any]]:
    """Laporan pemakaian per customer dalam rentang tanggal tertentu."""
    return await report_service.get_usage_report(db, _scope(current_user), date_from, date_to)


@router.get("/usage/export")
async def export_usage(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    date_from: date = Query(default_factory=lambda: date.today().replace(day=1)),
    date_to: date = Query(default_factory=date.today),
) -> Response:
    """Download CSV laporan pemakaian."""
    csv_content = await report_service.export_usage_csv(db, _scope(current_user), date_from, date_to)
    filename = f"usage_{date_from}_{date_to}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/usage/top-customers")
async def get_top_customers(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
) -> list[dict[str, Any]]:
    """Top customer berdasarkan pemakaian download."""
    return await report_service.get_top_customers_by_usage(db, _scope(current_user), limit=limit, days=days)


# ---------------------------------------------------------------------------
# Revenue Report
# ---------------------------------------------------------------------------


@router.get("/revenue")
async def get_revenue(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
) -> dict[str, Any]:
    """Laporan revenue (invoice & pembayaran) untuk periode bulan/tahun tertentu."""
    return await report_service.get_revenue_report(db, _scope(current_user), year, month)


@router.get("/revenue/export")
async def export_revenue(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    year: int = Query(default_factory=lambda: datetime.now().year),
    month: int = Query(default_factory=lambda: datetime.now().month, ge=1, le=12),
) -> Response:
    """Download CSV laporan revenue."""
    csv_content = await report_service.export_revenue_csv(db, _scope(current_user), year, month)
    filename = f"revenue_{year}_{month:02d}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Trend / Chart Data
# ---------------------------------------------------------------------------


@router.get("/revenue/trend")
async def get_revenue_trend(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
) -> list[dict[str, Any]]:
    """Data tren revenue bulanan untuk chart."""
    return await report_service.get_revenue_trend(db, _scope(current_user), months=months)


@router.get("/customer-growth")
async def get_customer_growth(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
) -> list[dict[str, Any]]:
    """Data pertumbuhan customer baru per bulan untuk chart."""
    return await report_service.get_customer_growth(db, _scope(current_user), months=months)
