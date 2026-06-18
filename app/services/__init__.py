"""Business logic services — placeholder package.

Services akan ditambahkan per domain, contoh:
- app/services/auth_service.py       — login, token management
- app/services/customer_service.py   — CRUD customer + RADIUS provisioning
- app/services/nas_service.py        — CRUD NAS + enkripsi shared secret
- app/services/billing_service.py    — kalkulasi expiry, kuota, invoice
- app/services/voucher_service.py    — generate & redeem voucher
- app/services/accounting_service.py — sinkronisasi radacct
- app/services/wallet_service.py     — manajemen saldo wallet

Aturan wajib:
- Semua business logic di sini, BUKAN di router.
- Router hanya parse request → panggil service → return response.
"""

from . import auth_service as auth_service
from . import billing_service as billing_service
from . import coa_service as coa_service
from . import customer_service as customer_service
from . import monitoring_service as monitoring_service
from . import nas_service as nas_service
from . import package_service as package_service
from . import vendor_profile_service as vendor_profile_service
from . import voucher_service as voucher_service
from . import wallet_service as wallet_service
