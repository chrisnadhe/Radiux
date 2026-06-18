"""API Endpoints untuk manajemen Invoicing dan Payment."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.models.admin_users import AdminUser
from app.models.payments import PaymentMethod
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])


def _get_tenant_id(user: "AdminUser") -> int | None:
    return None if user.is_superadmin else user.tenant_id


class PaymentRequest(BaseModel):
    customer_id: int
    amount: float
    method: PaymentMethod = PaymentMethod.CASH
    tenant_id: int | None = None
    invoice_id: int | None = None
    reference: str | None = None
    notes: str | None = None


class ManualInvoiceRequest(BaseModel):
    customer_id: int
    amount: float
    billing_period: str
    due_date: date
    tenant_id: int | None = None


@router.post("/generate-invoices", status_code=status.HTTP_200_OK)
async def api_generate_invoices(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Men-generate invoice bulanan secara manual (biasanya dipanggil oleh cron/scheduler)."""
    count = await billing_service.generate_monthly_invoices(db)
    return {"status": "success", "invoices_created": count}


@router.post("/invoice", status_code=status.HTTP_201_CREATED)
async def api_create_manual_invoice(
    req: ManualInvoiceRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Membuat invoice manual satuan."""
    from app.services import wallet_service

    if not user.is_superadmin:
        req.tenant_id = user.tenant_id
    elif not req.tenant_id:
        req.tenant_id = 1

    try:
        invoice = await billing_service.create_manual_invoice(
            db=db,
            customer_id=req.customer_id,
            amount=req.amount,
            billing_period=req.billing_period,
            due_date=req.due_date,
            tenant_id=req.tenant_id,
        )
        return {"status": "success", "invoice_id": invoice.id}
    except wallet_service.InsufficientBalanceError as e:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=str(e)) from e


@router.post("/pay", status_code=status.HTTP_201_CREATED)
async def api_record_payment(
    req: PaymentRequest, user: CurrentUser, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Mencatat pembayaran untuk customer/invoice tertentu."""
    if not user.is_superadmin:
        req.tenant_id = user.tenant_id
    elif not req.tenant_id:
        req.tenant_id = 1
    payment = await billing_service.record_payment(
        db=db,
        customer_id=req.customer_id,
        amount=req.amount,
        tenant_id=req.tenant_id,
        method=req.method,
        invoice_id=req.invoice_id,
        reference=req.reference,
        notes=req.notes,
    )
    return {"status": "success", "payment_id": payment.id}


@router.get("/invoices")
async def api_list_invoices(
    user: CurrentUser, tenant_id: int | None = None, db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Mendapatkan daftar invoice milik tenant."""
    scope_tenant_id = _get_tenant_id(user) or tenant_id
    if not scope_tenant_id and not user.is_superadmin:
        scope_tenant_id = user.tenant_id

    invoices = await billing_service.get_invoices(db, scope_tenant_id or 1)
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "billing_period": inv.billing_period,
            "due_date": inv.due_date,
            "amount": inv.amount,
            "status": inv.status,
            "paid_at": inv.paid_at,
        }
        for inv in invoices
    ]
