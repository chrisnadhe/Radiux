"""Service layer untuk Reporting & Dashboard Analytics (Phase 7)."""

import csv
import io
import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.customers import Customer
from app.models.invoices import Invoice, InvoiceStatus
from app.models.payments import Payment
from app.models.radius_core import RadAcct
from app.models.tenants import Tenant
from app.models.wallet_transactions import TransactionType, WalletTransaction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Usage Report
# ---------------------------------------------------------------------------


async def get_usage_report(
    db: AsyncSession,
    tenant_id: int | None,
    date_from: date,
    date_to: date,
) -> list[dict[str, Any]]:
    """Laporan pemakaian per customer (dari radacct).

    Mengembalikan list dict dengan session_count, durasi, upload, download.
    """
    date_from_dt = datetime.combine(date_from, datetime.min.time())
    date_to_dt = datetime.combine(date_to, datetime.max.time())

    query = (
        select(
            RadAcct.username,
            Customer.full_name,
            func.count(RadAcct.radacctid).label("session_count"),
            func.sum(RadAcct.acctsessiontime).label("total_seconds"),
            func.sum(RadAcct.acctinputoctets).label("upload_bytes"),
            func.sum(RadAcct.acctoutputoctets).label("download_bytes"),
        )
        .outerjoin(Customer, RadAcct.username == Customer.radius_username)
        .where(
            RadAcct.acctstarttime >= date_from_dt,
            RadAcct.acctstarttime <= date_to_dt,
        )
        .group_by(RadAcct.username, Customer.full_name)
        .order_by(func.sum(RadAcct.acctoutputoctets).desc())
    )

    if tenant_id is not None:
        query = query.where(Customer.tenant_id == tenant_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "username": r.username,
            "full_name": r.full_name or r.username,
            "session_count": r.session_count or 0,
            "total_seconds": int(r.total_seconds or 0),
            "upload_bytes": int(r.upload_bytes or 0),
            "download_bytes": int(r.download_bytes or 0),
            "upload_gb": round((r.upload_bytes or 0) / (1024**3), 3),
            "download_gb": round((r.download_bytes or 0) / (1024**3), 3),
            "duration_hours": round(int(r.total_seconds or 0) / 3600, 2),
        }
        for r in rows
    ]


async def get_top_customers_by_usage(
    db: AsyncSession,
    tenant_id: int | None,
    limit: int = 10,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Top customer berdasarkan download dalam N hari terakhir."""
    since = datetime.utcnow() - timedelta(days=days)  # noqa: DTZ003

    query = (
        select(
            RadAcct.username,
            Customer.full_name,
            func.sum(RadAcct.acctoutputoctets).label("download_bytes"),
            func.sum(RadAcct.acctinputoctets).label("upload_bytes"),
            func.count(RadAcct.radacctid).label("sessions"),
        )
        .outerjoin(Customer, RadAcct.username == Customer.radius_username)
        .where(RadAcct.acctstarttime >= since)
        .group_by(RadAcct.username, Customer.full_name)
        .order_by(func.sum(RadAcct.acctoutputoctets).desc())
        .limit(limit)
    )

    if tenant_id is not None:
        query = query.where(Customer.tenant_id == tenant_id)

    result = await db.execute(query)
    return [
        {
            "username": r.username,
            "full_name": r.full_name or r.username,
            "download_gb": round((r.download_bytes or 0) / (1024**3), 3),
            "upload_gb": round((r.upload_bytes or 0) / (1024**3), 3),
            "sessions": r.sessions or 0,
        }
        for r in result.all()
    ]


# ---------------------------------------------------------------------------
# Revenue Report
# ---------------------------------------------------------------------------


async def get_revenue_report(
    db: AsyncSession,
    tenant_id: int | None,
    year: int,
    month: int,
) -> dict[str, Any]:
    """Laporan revenue untuk bulan dan tahun tertentu.

    Mengembalikan summary, list invoice, breakdown per tenant, dan
    mutasi wallet per reseller.
    """
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    month_start_dt = datetime.combine(month_start, datetime.min.time())
    month_end_dt = datetime.combine(month_end, datetime.max.time())

    # Query invoice bulan ini
    inv_query = (
        select(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.tenant))
        .where(
            Invoice.created_at >= month_start_dt,
            Invoice.created_at <= month_end_dt,
        )
        .order_by(Invoice.created_at.desc())
    )
    if tenant_id is not None:
        inv_query = inv_query.where(Invoice.tenant_id == tenant_id)

    invoice_result = await db.scalars(inv_query)
    invoices = invoice_result.all()

    # Query total pembayaran diterima bulan ini
    pay_query = select(func.sum(Payment.amount)).where(
        Payment.payment_date >= month_start_dt,
        Payment.payment_date <= month_end_dt,
    )
    if tenant_id is not None:
        pay_query = pay_query.where(Payment.tenant_id == tenant_id)
    total_payment = float(await db.scalar(pay_query) or 0)

    # Summary
    total_invoice_amount = sum(float(inv.amount) for inv in invoices)
    paid_invoices = [inv for inv in invoices if inv.status == InvoiceStatus.PAID]
    total_paid = sum(float(inv.amount) for inv in paid_invoices)
    unpaid_count = len([inv for inv in invoices if inv.status == InvoiceStatus.UNPAID])

    # Breakdown per tenant (hanya superadmin)
    by_tenant: list[dict[str, Any]] = []
    wallet_summary: list[dict[str, Any]] = []

    if tenant_id is None:
        # Revenue per reseller
        tb_result = await db.execute(
            select(
                Invoice.tenant_id,
                Tenant.name.label("tenant_name"),
                func.count(Invoice.id).label("invoice_count"),
                func.sum(Invoice.amount).label("total_amount"),
            )
            .join(Tenant, Invoice.tenant_id == Tenant.id)
            .where(
                Invoice.created_at >= month_start_dt,
                Invoice.created_at <= month_end_dt,
            )
            .group_by(Invoice.tenant_id, Tenant.name)
            .order_by(func.sum(Invoice.amount).desc())
        )
        for r in tb_result.all():
            # Hitung paid amount untuk tenant ini
            paid_q = select(func.sum(Invoice.amount)).where(
                Invoice.tenant_id == r.tenant_id,
                Invoice.status == InvoiceStatus.PAID,
                Invoice.created_at >= month_start_dt,
                Invoice.created_at <= month_end_dt,
            )
            paid_amount = float(await db.scalar(paid_q) or 0)
            by_tenant.append(
                {
                    "tenant_id": r.tenant_id,
                    "tenant_name": r.tenant_name,
                    "invoice_count": r.invoice_count or 0,
                    "total_amount": float(r.total_amount or 0),
                    "paid_amount": paid_amount,
                }
            )

        # Mutasi wallet per reseller
        wt_result = await db.execute(
            select(
                WalletTransaction.tenant_id,
                Tenant.name.label("tenant_name"),
                WalletTransaction.transaction_type,
                func.sum(WalletTransaction.amount).label("total"),
            )
            .join(Tenant, WalletTransaction.tenant_id == Tenant.id)
            .where(
                WalletTransaction.created_at >= month_start_dt,
                WalletTransaction.created_at <= month_end_dt,
            )
            .group_by(
                WalletTransaction.tenant_id,
                Tenant.name,
                WalletTransaction.transaction_type,
            )
            .order_by(WalletTransaction.tenant_id)
        )
        wallet_by_tenant: dict[int, dict[str, Any]] = {}
        for r in wt_result.all():
            tid = r.tenant_id
            if tid not in wallet_by_tenant:
                wallet_by_tenant[tid] = {
                    "tenant_id": tid,
                    "tenant_name": r.tenant_name,
                    "topup": 0.0,
                    "deduction": 0.0,
                }
            if r.transaction_type == TransactionType.TOPUP:
                wallet_by_tenant[tid]["topup"] = float(r.total or 0)
            else:
                wallet_by_tenant[tid]["deduction"] = float(r.total or 0)
        wallet_summary = list(wallet_by_tenant.values())

    return {
        "period": f"{month:02d}/{year}",
        "month_start": month_start.isoformat(),
        "month_end": month_end.isoformat(),
        "summary": {
            "total_invoices": len(invoices),
            "paid_invoices": len(paid_invoices),
            "unpaid_invoices": unpaid_count,
            "total_invoice_amount": total_invoice_amount,
            "total_paid_amount": total_paid,
            "total_payments_received": total_payment,
            "collection_rate": (round(total_paid / total_invoice_amount * 100, 1) if total_invoice_amount else 0),
        },
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "customer_name": inv.customer.full_name if inv.customer else "-",
                "tenant_name": inv.tenant.name if inv.tenant else "-",
                "billing_period": inv.billing_period,
                "amount": float(inv.amount),
                "status": inv.status.value,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            }
            for inv in invoices
        ],
        "by_tenant": by_tenant,
        "wallet_summary": wallet_summary,
    }


# ---------------------------------------------------------------------------
# Trend / Chart Data
# ---------------------------------------------------------------------------


async def get_revenue_trend(
    db: AsyncSession,
    tenant_id: int | None,
    months: int = 6,
) -> list[dict[str, Any]]:
    """Revenue bulanan N bulan terakhir untuk chart."""
    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        # Hitung tanggal bulan ke-i yang lalu
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        start_dt = datetime.combine(month_start, datetime.min.time())
        end_dt = datetime.combine(next_month - timedelta(days=1), datetime.max.time())

        q_inv = select(func.sum(Invoice.amount)).where(
            Invoice.created_at >= start_dt,
            Invoice.created_at <= end_dt,
        )
        q_pay = select(func.sum(Payment.amount)).where(
            Payment.payment_date >= start_dt,
            Payment.payment_date <= end_dt,
        )
        if tenant_id is not None:
            q_inv = q_inv.where(Invoice.tenant_id == tenant_id)
            q_pay = q_pay.where(Payment.tenant_id == tenant_id)

        invoice_total = float(await db.scalar(q_inv) or 0)
        payment_total = float(await db.scalar(q_pay) or 0)

        result.append(
            {
                "label": month_start.strftime("%b %Y"),
                "invoice_amount": invoice_total,
                "payment_amount": payment_total,
            }
        )

    return result


async def get_customer_growth(
    db: AsyncSession,
    tenant_id: int | None,
    months: int = 6,
) -> list[dict[str, Any]]:
    """Jumlah customer baru per bulan N bulan terakhir."""
    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1

        month_start = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        start_dt = datetime.combine(month_start, datetime.min.time())
        end_dt = datetime.combine(next_month - timedelta(days=1), datetime.max.time())

        q = select(func.count(Customer.id)).where(
            Customer.created_at >= start_dt,
            Customer.created_at <= end_dt,
        )
        if tenant_id is not None:
            q = q.where(Customer.tenant_id == tenant_id)

        count = int(await db.scalar(q) or 0)
        result.append({"label": month_start.strftime("%b %Y"), "count": count})

    return result


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------


async def export_usage_csv(
    db: AsyncSession,
    tenant_id: int | None,
    date_from: date,
    date_to: date,
) -> str:
    """Generate CSV string dari usage report."""
    rows = await get_usage_report(db, tenant_id, date_from, date_to)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Username", "Nama Customer", "Jumlah Sesi", "Durasi (Jam)", "Upload (GB)", "Download (GB)"])
    for r in rows:
        writer.writerow(
            [
                r["username"],
                r["full_name"],
                r["session_count"],
                r["duration_hours"],
                r["upload_gb"],
                r["download_gb"],
            ]
        )
    return output.getvalue()


async def export_revenue_csv(
    db: AsyncSession,
    tenant_id: int | None,
    year: int,
    month: int,
) -> str:
    """Generate CSV string dari revenue report."""
    data = await get_revenue_report(db, tenant_id, year, month)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "No. Invoice",
            "Customer",
            "Tenant/Reseller",
            "Periode",
            "Jumlah (Rp)",
            "Status",
            "Jatuh Tempo",
            "Tanggal Lunas",
        ]
    )
    for inv in data["invoices"]:
        writer.writerow(
            [
                inv["invoice_number"],
                inv["customer_name"],
                inv["tenant_name"],
                inv["billing_period"],
                inv["amount"],
                inv["status"],
                inv["due_date"] or "",
                inv["paid_at"] or "",
            ]
        )
    return output.getvalue()
