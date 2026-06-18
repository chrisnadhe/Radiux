"""API Endpoints untuk manajemen Invoicing dan Payment."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import date
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.payments import PaymentMethod
from app.services import billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])

class PaymentRequest(BaseModel):
    customer_id: int
    amount: float
    method: PaymentMethod = PaymentMethod.CASH
    tenant_id: int = 1
    invoice_id: int | None = None
    reference: str | None = None
    notes: str | None = None

class ManualInvoiceRequest(BaseModel):
    customer_id: int
    amount: float
    billing_period: str
    due_date: date
    tenant_id: int = 1

@router.post("/generate-invoices", status_code=status.HTTP_200_OK)
async def api_generate_invoices(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Men-generate invoice bulanan secara manual (biasanya dipanggil oleh cron/scheduler)."""
    count = await billing_service.generate_monthly_invoices(db)
    return {"status": "success", "invoices_created": count}

@router.post("/invoice", status_code=status.HTTP_201_CREATED)
async def api_create_manual_invoice(
    req: ManualInvoiceRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Membuat invoice manual satuan."""
    invoice = await billing_service.create_manual_invoice(
        db=db,
        customer_id=req.customer_id,
        amount=req.amount,
        billing_period=req.billing_period,
        due_date=req.due_date,
        tenant_id=req.tenant_id
    )
    return {"status": "success", "invoice_id": invoice.id}

@router.post("/pay", status_code=status.HTTP_201_CREATED)
async def api_record_payment(
    req: PaymentRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """Mencatat pembayaran untuk customer/invoice tertentu."""
    payment = await billing_service.record_payment(
        db=db,
        customer_id=req.customer_id,
        amount=req.amount,
        tenant_id=req.tenant_id,
        method=req.method,
        invoice_id=req.invoice_id,
        reference=req.reference,
        notes=req.notes
    )
    return {"status": "success", "payment_id": payment.id}

@router.get("/invoices")
async def api_list_invoices(
    tenant_id: int = 1,
    db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Mendapatkan daftar invoice milik tenant."""
    invoices = await billing_service.get_invoices(db, tenant_id)
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "billing_period": inv.billing_period,
            "due_date": inv.due_date,
            "amount": inv.amount,
            "status": inv.status,
            "paid_at": inv.paid_at
        } for inv in invoices
    ]
