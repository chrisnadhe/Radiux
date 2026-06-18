"""Business logic services — placeholder package.

Services akan ditambahkan per domain, contoh:
- app/services/auth_service.py       — login, token management
- app/services/customer_service.py   — CRUD customer + RADIUS provisioning
- app/services/nas_service.py        — CRUD NAS + enkripsi shared secret
- app/services/billing_service.py    — kalkulasi expiry, kuota, invoice
- app/services/voucher_service.py    — generate & redeem voucher
- app/services/accounting_service.py — sinkronisasi radacct

Aturan wajib:
- Semua business logic di sini, BUKAN di router.
- Router hanya parse request → panggil service → return response.
"""
