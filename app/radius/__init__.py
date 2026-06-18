"""RADIUS client — placeholder package.

Akan berisi implementasi pyrad untuk CoA/Disconnect (Phase 4):
- app/radius/client.py          — RADIUS UDP client (pyrad wrapper)
- app/radius/vendor_mapper.py   — mapping atribut per vendor profile
- app/radius/packet_builder.py  — builder paket CoA-Request / Disconnect-Request

Aturan wajib:
- Semua koneksi UDP RADIUS (CoA/Disconnect) hanya boleh dibuat dari sini.
- Jangan buat koneksi RADIUS dari router, service, atau jobs lain.
"""
