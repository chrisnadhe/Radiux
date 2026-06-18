"""Background jobs — placeholder package.

Akan berisi APScheduler tasks (Phase 5+), contoh:
- app/jobs/expiry_checker.py    — auto-suspend pelanggan expired / kuota habis
- app/jobs/voucher_cleanup.py   — cleanup voucher expired
- app/jobs/notification_sender.py — kirim notifikasi email/WA/Telegram
- app/jobs/accounting_sync.py   — agregasi data radacct untuk billing

Akan dimigrasi ke Celery + Redis saat skala besar (lihat PLAN.md seksi 3).
"""
