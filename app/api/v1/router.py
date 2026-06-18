"""Router utama API v1 — agregasi semua sub-router domain."""

from fastapi import APIRouter

# ---------------------------------------------------------------------------
# Sub-router domain akan di-import di sini seiring development berlanjut.
# Contoh (Phase 1+):
#   from app.api.v1 import auth, customers, nas, billing, monitoring
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1")

# ---------------------------------------------------------------------------
# Health check — endpoint internal untuk liveness probe Docker/K8s
# ---------------------------------------------------------------------------
# Catatan: endpoint /health ada di app.main (root level, tanpa prefix /api/v1)
# agar mudah dicek dari luar tanpa autentikasi.
# Di sini hanya placeholder untuk sub-router masa depan.
# ---------------------------------------------------------------------------

# Phase 1+: uncomment dan tambahkan router domain
# router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
# router.include_router(customers.router, prefix="/customers", tags=["Customers"])
# router.include_router(nas.router, prefix="/nas", tags=["NAS"])
# router.include_router(billing.router, prefix="/billing", tags=["Billing"])
# router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
