"""Router utama API v1 — agregasi semua sub-router domain."""

from fastapi import APIRouter

from app.api.v1 import auth, customers, nas, packages

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Domain routers — Phase 1
# ---------------------------------------------------------------------------
router.include_router(auth.router, tags=["Authentication"])
router.include_router(customers.router, tags=["Customers"])
router.include_router(packages.router, tags=["Packages"])
router.include_router(nas.router, tags=["NAS"])

# Phase 2+: monitoring, billing, vouchers, tenants
