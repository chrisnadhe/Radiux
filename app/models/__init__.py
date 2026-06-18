"""Models package — export semua ORM models.

Import urutan penting untuk Alembic autogenerate:
1. Base (dari database.py)
2. Tabel ekstensi Radiux (yang dikelola Alembic)
3. Tabel inti FreeRADIUS (radius_core — excluded dari Alembic, import
   hanya agar ORM dapat dipakai untuk query)
"""

# Tabel ekstensi Radiux (dikelola Alembic)
from app.models.admin_users import AdminRole, AdminUser  # noqa: F401
from app.models.customers import Customer, CustomerStatus  # noqa: F401
from app.models.invoices import Invoice, InvoiceStatus  # noqa: F401
from app.models.nas_ext import NasExt  # noqa: F401
from app.models.nas_vendor_profiles import NasVendorProfile, RateLimitFormat  # noqa: F401
from app.models.notifications import (  # noqa: F401
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationStatus,
)
from app.models.packages import Package, PackageType  # noqa: F401
from app.models.payments import Payment, PaymentMethod  # noqa: F401

# Tabel inti FreeRADIUS (tidak dikelola Alembic — schema.sql)
from app.models.radius_core import (  # noqa: F401
    NasCore,
    RadAcct,
    RadCheck,
    RadGroupCheck,
    RadGroupReply,
    RadPostAuth,
    RadReply,
    RadUserGroup,
)
from app.models.tenants import Tenant, TenantStatus  # noqa: F401
from app.models.vouchers import VoucherBatch  # noqa: F401
from app.models.wallet_transactions import TransactionType, WalletTransaction  # noqa: F401

__all__ = [
    # Radiux extension
    "AdminRole",
    "AdminUser",
    "Customer",
    "CustomerStatus",
    "NasVendorProfile",
    "NasExt",
    "Notification",
    "NotificationChannel",
    "NotificationEventType",
    "NotificationStatus",
    "Package",
    "PackageType",
    "RateLimitFormat",
    "Tenant",
    "TenantStatus",
    "VoucherBatch",
    "Invoice",
    "InvoiceStatus",
    "Payment",
    "PaymentMethod",
    "WalletTransaction",
    "TransactionType",
    # FreeRADIUS core (read-only)
    "NasCore",
    "RadAcct",
    "RadCheck",
    "RadGroupCheck",
    "RadGroupReply",
    "RadPostAuth",
    "RadReply",
    "RadUserGroup",
]
