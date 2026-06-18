"""Service layer untuk operasi tagihan dan pembayaran (Invoicing & Payment)."""

import logging
from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customers import Customer, CustomerStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.packages import Package, PackageType
from app.models.payments import Payment, PaymentMethod
from sqlalchemy.orm import joinedload
from app.services.coa_service import kick_user

logger = logging.getLogger(__name__)

async def generate_monthly_invoices(db: AsyncSession) -> int:
    """Menerbitkan tagihan bulanan untuk semua pelanggan Pascabayar.
    Idealnya dijalankan tiap tanggal 1 (atau sesuai siklus penagihan).
    """
    # Cari customer postpaid yang masih aktif
    # Pelanggan dengan package_type = POSTPAID
    stmt = select(Customer).join(Package).where(
        Customer.status.in_([CustomerStatus.ACTIVE, CustomerStatus.SUSPENDED]),
        Customer.is_active == True,
        Package.package_type == PackageType.POSTPAID
    ).options(joinedload(Customer.package))
    result = await db.scalars(stmt)
    customers = result.all()

    invoices_created = 0
    current_date = date.today()
    billing_period = current_date.strftime("%B %Y")  # ex: June 2026
    
    # Jatuh tempo 7 hari dari sekarang
    due_date = current_date + timedelta(days=7)

    for cust in customers:
        if not cust.package:
            continue
            
        # Cek apakah invoice bulan ini sudah ada agar tidak ganda
        exist_stmt = select(Invoice).where(
            Invoice.customer_id == cust.id,
            Invoice.billing_period == billing_period
        )
        exist = await db.scalar(exist_stmt)
        if exist:
            continue
            
        inv_number = f"INV-{current_date.strftime('%Y%m')}-{cust.id:04d}"
        
        invoice = Invoice(
            invoice_number=inv_number,
            customer_id=cust.id,
            billing_period=billing_period,
            due_date=due_date,
            amount=cust.package.price,
            tenant_id=cust.tenant_id,
            status=InvoiceStatus.UNPAID
        )
        db.add(invoice)
        invoices_created += 1

    await db.commit()
    logger.info(f"Berhasil generate {invoices_created} invoices untuk periode {billing_period}.")
    return invoices_created

async def create_manual_invoice(
    db: AsyncSession,
    customer_id: int,
    amount: float,
    billing_period: str,
    due_date: date,
    tenant_id: int
) -> Invoice:
    """Membuat invoice satuan secara manual untuk pelanggan tertentu."""
    inv_number = f"INV-{date.today().strftime('%Y%m')}-{customer_id:04d}-M"
    
    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=customer_id,
        billing_period=billing_period,
        due_date=due_date,
        amount=amount,
        tenant_id=tenant_id,
        status=InvoiceStatus.UNPAID
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)
    return invoice

async def record_payment(
    db: AsyncSession, 
    customer_id: int, 
    amount: float, 
    tenant_id: int, 
    method: PaymentMethod = PaymentMethod.CASH,
    invoice_id: int | None = None,
    reference: str | None = None,
    notes: str | None = None
) -> Payment:
    """Mencatat pembayaran, melunasi invoice (jika ada), dan mengaktifkan kembali sesi jika disuspend."""
    
    payment = Payment(
        customer_id=customer_id,
        amount=amount,
        method=method,
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        reference=reference,
        notes=notes
    )
    db.add(payment)
    
    # Jika bayar tagihan, lunasi invoice tersebut
    if invoice_id:
        invoice = await db.scalar(select(Invoice).where(Invoice.id == invoice_id))
        if invoice and invoice.status == InvoiceStatus.UNPAID:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.now()
            
    # Jika customer sebelumnya SUSPENDED (karena telat bayar), ubah jadi ACTIVE
    customer = await db.scalar(select(Customer).where(Customer.id == customer_id))
    if customer and customer.status == CustomerStatus.SUSPENDED:
        customer.status = CustomerStatus.ACTIVE
        # Jika ada router RADIUS yg menggunakan radusergroup untuk suspend, pastikan 
        # service ini atau scheduler mengembalikan paket aslinya.
        # (Akan dihandle sinkronisasi jika dibutuhkan).

    await db.commit()
    await db.refresh(payment)
    return payment

async def get_invoices(db: AsyncSession, tenant_id: int) -> Sequence[Invoice]:
    """Mendapatkan daftar invoice tenant."""
    result = await db.scalars(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.tenant_id == tenant_id)
        .order_by(Invoice.created_at.desc())
    )
    return result.all()

async def get_invoice_with_customer(db: AsyncSession, invoice_id: int, tenant_id: int) -> Invoice | None:
    """Mendapatkan satu invoice beserta data customer."""
    result = await db.scalar(
        select(Invoice)
        .options(joinedload(Invoice.customer))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    return result
