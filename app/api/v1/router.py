"""Router utama API v1 — agregasi semua sub-router domain."""

from fastapi import APIRouter

from app.api.v1 import (
    admin_users,
    audit,
    auth,
    billing,
    customers,
    monitoring,
    nas,
    notifications,
    packages,
    reports,
    sessions,
    tenants,
    vendor_profiles,
    vouchers,
)

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Domain routers — Phase 1
# ---------------------------------------------------------------------------
router.include_router(auth.router, tags=["Authentication"])
router.include_router(customers.router, tags=["Customers"])
router.include_router(packages.router, tags=["Packages"])
router.include_router(nas.router, tags=["NAS"])
router.include_router(sessions.router, tags=["Sessions"])
router.include_router(billing.router, tags=["Billing"])
router.include_router(vouchers.router, tags=["Vouchers"])
router.include_router(audit.router, tags=["Audit"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 2: Multi-Vendor NAS
# ---------------------------------------------------------------------------
router.include_router(vendor_profiles.router, tags=["Vendor Profiles"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 3: Monitoring
# ---------------------------------------------------------------------------
router.include_router(monitoring.router, tags=["Monitoring"])

# Phase 4+: coa, billing, vouchers, tenants, admin_users
router.include_router(tenants.router, tags=["Tenants"])
router.include_router(admin_users.router, tags=["Admin Users"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 7: Reporting & Dashboard
# ---------------------------------------------------------------------------
router.include_router(reports.router, tags=["Reports"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 8: Notifications
# ---------------------------------------------------------------------------
router.include_router(notifications.router, tags=["Notifications"])
