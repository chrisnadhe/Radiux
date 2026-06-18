"""Router utama API v1 — agregasi semua sub-router domain."""

from fastapi import APIRouter

from app.api.v1 import auth, customers, monitoring, nas, packages, vendor_profiles

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Domain routers — Phase 1
# ---------------------------------------------------------------------------
router.include_router(auth.router, tags=["Authentication"])
router.include_router(customers.router, tags=["Customers"])
router.include_router(packages.router, tags=["Packages"])
router.include_router(nas.router, tags=["NAS"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 2: Multi-Vendor NAS
# ---------------------------------------------------------------------------
router.include_router(vendor_profiles.router, tags=["Vendor Profiles"])

# ---------------------------------------------------------------------------
# Domain routers — Phase 3: Monitoring
# ---------------------------------------------------------------------------
router.include_router(monitoring.router, tags=["Monitoring"])

# Phase 4+: coa, billing, vouchers, tenants
