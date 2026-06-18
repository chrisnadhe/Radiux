# Radiux — Rencana Pengembangan Full Application

Dokumen ini adalah rencana pengembangan lengkap (bukan hanya MVP) untuk Radiux, Web UI pengelola FreeRADIUS untuk kebutuhan ISP: AAA, Hotspot, Billing/Voucher, Multi-Reseller, dan Monitoring real-time dengan dukungan multi-vendor NAS.

## 1. Visi & Tujuan

Radiux ditujukan sebagai panel operasional tunggal bagi ISP untuk mengelola seluruh siklus hidup pelanggan internet: dari provisioning user RADIUS, manajemen NAS lintas vendor, monitoring sesi real-time, hingga billing dan reseller management — tanpa perlu menyentuh file konfigurasi FreeRADIUS secara manual.

Prinsip desain utama:
- **Zero-downtime provisioning** — perubahan user/paket langsung aktif tanpa restart FreeRADIUS.
- **Vendor-agnostic** — satu UI untuk Mikrotik, Cisco, Ubiquiti, Huawei, Cambium, dan vendor lain via abstraksi profil.
- **Multi-tenant by design** — bukan tambahan di belakang, tapi bagian dari skema data sejak awal.
- **Auditable** — setiap aksi admin/reseller tercatat untuk kebutuhan troubleshooting dan kepatuhan.

## 2. Keputusan Arsitektur

### 2.1 Integrasi dengan FreeRADIUS — Shared Database (SQL Backend)

Radiux dan FreeRADIUS berbagi satu instance PostgreSQL. FreeRADIUS dikonfigurasi memakai modul `rlm_sql` dengan skema standar:

- `radcheck`, `radreply` — atribut autentikasi & autorisasi per user
- `radgroupcheck`, `radgroupreply` — atribut per grup/paket (memudahkan ganti paket massal)
- `radacct` — data accounting (sesi, durasi, byte in/out) — sumber utama untuk monitoring & billing kuota
- `radpostauth` — log percobaan login (sukses/gagal) — sumber untuk audit & deteksi brute force
- `nas` — daftar perangkat NAS beserta shared secret

Keuntungan pendekatan ini: tidak perlu reload/restart FreeRADIUS setiap kali ada user baru atau perubahan paket, karena FreeRADIUS query langsung ke DB di setiap request autentikasi.

### 2.2 CoA & Disconnect — RADIUS Client Terpisah

Operasi Disconnect-Request dan CoA-Request (RFC 5176) **tidak lewat jalur SQL** — ini paket UDP yang dikirim langsung dari Radiux ke NAS. Radiux mengimplementasikan RADIUS client sendiri (memakai pustaka seperti `pyrad`) yang menyimpan mapping atribut per vendor (lihat 2.3) untuk menyusun paket yang sesuai dengan masing-masing merk NAS.

### 2.3 Multi-Vendor NAS — Vendor Profile Abstraction

Setiap NAS yang didaftarkan di Radiux diasosiasikan dengan satu **Vendor Profile** yang mendefinisikan:
- Dictionary atribut RADIUS yang dipakai (file dictionary FreeRADIUS per vendor)
- Mapping atribut untuk rate-limit/bandwidth (contoh: `Mikrotik-Rate-Limit` vs atribut Cisco/Ubiquiti yang berbeda)
- Format atribut untuk CoA/Disconnect (beberapa vendor butuh `NAS-IP-Address` + `Acct-Session-Id`, sebagian butuh `User-Name` saja)

Admin tinggal pilih vendor dari dropdown saat menambah NAS baru; Radiux otomatis menyusun atribut yang sesuai di belakang layar.

### 2.4 Multi-Tenant / Reseller

Model hierarki dua level: **Superadmin → Reseller → Customer**. Setiap baris data customer-related (user RADIUS, voucher, invoice) punya kolom `tenant_id`/`reseller_id` untuk scoping. RBAC diterapkan di level aplikasi (FastAPI dependency injection per-request), bukan row-level security di Postgres pada fase awal — opsi RLS Postgres dipertimbangkan ulang di fase hardening (Phase 9) jika diperlukan isolasi lebih ketat.

### 2.5 Realtime Monitoring

Dashboard sesi aktif memakai **Server-Sent Events (SSE)** yang di-push dari backend FastAPI, dikonsumsi langsung oleh HTMX (`hx-ext="sse"`) tanpa perlu JavaScript custom. Data sesi diambil dari polling `radacct` (interim updates) dengan interval pendek, bukan dari NAS langsung — agar tidak menambah beban ke perangkat NAS.

## 3. Tech Stack & Alasan

| Komponen | Pilihan | Alasan |
|---|---|---|
| Backend | FastAPI | Familiar untuk tim, async-native, cocok untuk I/O-bound (DB + RADIUS packet) |
| Frontend | HTMX + TailwindCSS | Server-rendered, minim JS, cepat dikembangkan, cocok untuk dashboard CRUD-heavy |
| Database | PostgreSQL | Didukung native oleh FreeRADIUS `rlm_sql`, robust untuk concurrent write (radacct) |
| Package Manager | uv | Resolusi dependensi cepat, lockfile deterministik |
| Background Jobs | APScheduler (awal) → Celery+Redis (saat skala besar) | Untuk expiry check, voucher batch, notifikasi terjadwal |
| Realtime | SSE | Lebih ringan dari WebSocket untuk kasus one-way push, native didukung HTMX |
| RADIUS Client | pyrad | Implementasi RFC 2865/2866/5176 yang matang di Python |

## 4. Desain Skema Database

### 4.1 Tabel Inti FreeRADIUS (tidak diubah strukturnya, standar `rlm_sql`)
`radcheck`, `radreply`, `radgroupcheck`, `radgroupreply`, `radusergroup`, `radacct`, `radpostauth`, `nas`

### 4.2 Tabel Ekstensi Radiux

| Tabel | Fungsi |
|---|---|
| `tenants` | Data reseller/tenant (nama, status, saldo, level hierarki) |
| `admin_users` | Akun login Radiux (superadmin/reseller/operator/viewer) + role |
| `customers` | Data pelanggan end-user, relasi ke `radcheck`/`radusergroup`, relasi ke `tenant_id` |
| `packages` | Paket layanan (nama, speed profile, kuota, harga, validity period) |
| `nas_vendor_profiles` | Mapping atribut per vendor (lihat 2.3) |
| `vouchers` | Kode voucher prepaid, status (unused/used/expired), relasi ke `package_id` & `tenant_id` |
| `invoices` | Invoice postpaid, status pembayaran, due date |
| `payments` | Histori pembayaran (manual entry atau gateway) |
| `tenant_wallets` / `wallet_transactions` | Saldo reseller & log mutasi (topup, komisi, deduksi) |
| `audit_logs` | Log semua aksi admin/reseller (siapa, kapan, aksi apa, before/after) |
| `notifications` | Log notifikasi terkirim (expiry, low balance, NAS down) |

## 5. Arsitektur Aplikasi

```
Browser (HTMX) <—HTTP/SSE—> FastAPI App <—SQL—> PostgreSQL <—rlm_sql—> FreeRADIUS
                                  |                                         |
                                  '——— UDP (CoA/Disconnect, via pyrad) —————'
                                  |
                              Redis (cache, job queue)
                                  |
                          APScheduler/Celery worker (billing expiry, notifikasi)
```

## 6. Rencana Fase Pengembangan

Setiap fase dianggap selesai ketika fitur-fiturnya berfungsi end-to-end (bukan sekadar UI tanpa backend).

**Phase 0 — Foundation**
Setup repo, `pyproject.toml` + uv lockfile, struktur folder, Dockerfile multi-stage (app, freeradius, postgres), docker-compose skeleton, base FastAPI app + health check, CI dasar (lint + test).

**Phase 1 — Core AAA**
Model `radcheck`/`radreply`/`radusergroup`, CRUD customer & package, CRUD NAS, integrasi awal dengan FreeRADIUS via `rlm_sql`, uji autentikasi end-to-end dari NAS dummy/test client.

**Phase 2 — Multi-Vendor NAS & Hotspot**
`nas_vendor_profiles`, dictionary loader per vendor, UI pemilihan vendor saat tambah NAS, mapping atribut bandwidth/rate-limit otomatis sesuai paket.

**Phase 3 — Accounting & Real-time Monitoring**
Ingestion `radacct`, dashboard sesi aktif, grafik penggunaan bandwidth/kuota, live table via HTMX + SSE, status NAS (online/offline berdasarkan last accounting interim).

**Phase 4 — CoA & Disconnect**
Implementasi RADIUS client (pyrad), tombol "Kick User" dan "Ganti Paket On-the-Fly" di UI, template atribut CoA per vendor, logging hasil tiap operasi.

**Phase 5 — Billing & Voucher**
Manajemen `packages`, generate voucher batch (dengan opsi export PDF untuk cetak), invoice untuk postpaid, pencatatan pembayaran manual, job terjadwal untuk auto-suspend saat expired/kuota habis.

**Phase 6 — Multi-Tenant / Reseller**
RBAC penuh (superadmin/reseller/operator/viewer), scoping data per `tenant_id`, dashboard reseller (saldo, komisi, customer sendiri), self-service portal reseller untuk generate voucher dari saldo sendiri.

**Phase 7 — Reporting & Dashboard**
Laporan pemakaian, laporan revenue per reseller/periode, export CSV, dashboard ringkasan untuk superadmin (total user aktif, NAS online, revenue bulanan).

**Phase 8 — Notifikasi**
Integrasi email/WhatsApp/Telegram untuk alert expiry, saldo reseller menipis, NAS down, dengan template pesan yang bisa dikustomisasi.

**Phase 9 — Keamanan & Audit**
2FA untuk admin/reseller, `audit_logs` lengkap di semua aksi sensitif, rate limiting di endpoint login & API publik, evaluasi kebutuhan Row-Level Security di Postgres, secret rotation untuk shared secret NAS.

**Phase 10 — Testing & QA**
Unit test (services & RADIUS client logic), integration test (DB + FreeRADIUS via docker-compose test environment), load test untuk throughput AAA (target sesuai skala ISP target), test multi-vendor CoA dengan emulator NAS per vendor jika tersedia.

**Phase 11 — Deployment & DevOps**
Finalisasi `docker-compose.yml` produksi (app, freeradius, postgres, redis, reverse proxy/nginx, optional Prometheus+Grafana untuk metrics), script backup/restore database, dokumentasi upgrade path antar versi.

**Phase 12 — Dokumentasi & Launch**
Manual pengguna (admin & reseller), dokumentasi API (otomatis via FastAPI OpenAPI + penjelasan tambahan), admin guide untuk instalasi produksi, checklist go-live.

## 7. Struktur Direktori Proyek

```
radiux/
├── app/
│   ├── api/v1/                # routers per domain (auth, customers, nas, billing, monitoring)
│   ├── core/                  # config, security, dependencies, RBAC
│   ├── models/                # SQLAlchemy: radius core + extension tables
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # business logic (billing, voucher, coa, accounting_sync)
│   ├── radius/                  # pyrad client, vendor attribute mapper
│   ├── jobs/                     # APScheduler/Celery tasks
│   ├── templates/                 # Jinja2 + HTMX partials (per modul)
│   └── static/                     # Tailwind build output
├── freeradius/
│   ├── mods-config/sql/
│   └── dictionary.vendor/
├── migrations/                       # Alembic
├── tests/
├── docker/
├── docker-compose.yml
├── docker-compose.prod.yml
├── pyproject.toml
├── README.md
└── PLAN.md
```

## 8. Strategi Testing

- **Unit test**: logic billing (kalkulasi expiry, kuota), vendor attribute mapper, RBAC dependency.
- **Integration test**: jalankan FreeRADIUS + Postgres via docker-compose test profile, kirim paket auth/accounting sungguhan, verifikasi end-to-end.
- **CoA/Disconnect test**: emulator NAS sederhana (listener UDP) per vendor untuk verifikasi format paket tanpa hardware fisik.
- **Load test**: simulasikan ratusan/ribuan auth-request per detik (sesuai target skala) untuk memastikan tidak ada bottleneck di layer SQL.

## 9. Strategi Deployment

Docker Compose dengan service terpisah:

```
services:
  app:        # FastAPI + uv, Dockerfile menginstall semua dependency saat build
  freeradius: # FreeRADIUS 3.x dengan mods-config/sql terhubung ke postgres
  postgres:   # Database bersama
  redis:      # Cache & job queue
  nginx:      # Reverse proxy + TLS termination (produksi)
```

Satu command (`docker compose up -d --build`) menangani instalasi seluruh dependensi (Python packages via uv di image app, FreeRADIUS package di image freeradius) sehingga tidak ada langkah instalasi manual terpisah di host.

## 10. Keamanan

- Semua shared secret NAS disimpan terenkripsi di DB (bukan plaintext), didekripsi hanya saat dibutuhkan untuk komunikasi RADIUS.
- RBAC ketat: reseller tidak bisa mengakses data tenant lain di level query (filter wajib di setiap repository method, bukan opsional di controller).
- Audit log untuk semua operasi create/update/delete pada data sensitif (user, paket, voucher, NAS, saldo).
- Rate limiting di endpoint auth Radiux (bukan FreeRADIUS) untuk mencegah brute force ke panel admin.

## 11. Roadmap Timeline (Estimasi Kasar)

| Fase | Estimasi |
|---|---|
| Phase 0–1 (Foundation + Core AAA) | 3–4 minggu |
| Phase 2–4 (Multi-vendor, Monitoring, CoA) | 4–5 minggu |
| Phase 5–6 (Billing, Multi-tenant) | 4–5 minggu |
| Phase 7–9 (Reporting, Notifikasi, Security) | 3–4 minggu |
| Phase 10–12 (Testing, Deployment, Dokumentasi) | 2–3 minggu |

Estimasi ini asumsi tim kecil (1–2 developer); sesuaikan kembali setelah Phase 0 selesai dan velocity tim diketahui.

## 12. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Perbedaan atribut RADIUS antar vendor lebih kompleks dari perkiraan | Mulai dengan 2–3 vendor populer (Mikrotik, Ubiquiti, Cisco), tambah vendor lain secara inkremental |
| Beban query `radacct` tinggi saat user banyak | Indexing yang tepat, pertimbangkan partisi tabel per bulan di skala besar |
| CoA tidak didukung penuh oleh sebagian NAS vendor | Dokumentasikan kompatibilitas per vendor, fallback ke disconnect manual via API NAS jika tersedia |
| Scope creep dari fitur billing yang kompleks | Kunci skema `packages`/`vouchers`/`invoices` di Phase 5, hindari fitur akuntansi penuh (itu di luar scope Radiux) |

## 13. Langkah Selanjutnya

1. Finalisasi skema database (Phase 1) dan migrasi awal.
2. Setup docker-compose dasar dengan FreeRADIUS + Postgres yang sudah saling terhubung via `rlm_sql`.
3. Implementasi CRUD customer/NAS dasar untuk validasi arsitektur sebelum lanjut ke fitur lanjutan.
