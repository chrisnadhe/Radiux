# Radiux

Web UI modern untuk mengelola **FreeRADIUS** — AAA (Authentication, Authorization, Accounting), Hotspot, Billing/Voucher, dan Multi-Reseller, dirancang khusus untuk kebutuhan operasional ISP dengan dukungan **multi-vendor NAS** (Mikrotik, Cisco, Ubiquiti, Huawei, Cambium, dll).

> Status: dalam pengembangan. Lihat [`PLAN.md`](./PLAN.md) untuk roadmap lengkap dan keputusan arsitektur.

## Fitur Utama

- **AAA & Hotspot Management** — kelola user, NAS, profil bandwidth, dan dictionary multi-vendor dari satu dashboard.
- **Real-time Monitoring** — pantau sesi aktif, trafik, dan status NAS secara live.
- **CoA & Disconnect** — putuskan koneksi user atau ubah paket bandwidth on-the-fly tanpa re-login.
- **Billing & Voucher** — paket prepaid/postpaid, generate voucher batch, invoice, dan pencatatan pembayaran.
- **Multi-Tenant / Reseller** — setiap reseller punya kuota, saldo, dan customer sendiri dengan isolasi data penuh.

## Tech Stack

| Layer | Teknologi |
|---|---|
| Backend | FastAPI (Python) |
| Frontend | HTMX + TailwindCSS (server-rendered via Jinja2, tanpa SPA framework) |
| Database | PostgreSQL (shared dengan FreeRADIUS via `rlm_sql`) |
| RADIUS Server | FreeRADIUS 3.x |
| Package Manager | uv |
| Background Jobs | APScheduler / Celery + Redis |
| Realtime Updates | Server-Sent Events (SSE) |
| Containerization | Docker & Docker Compose |

## Arsitektur Singkat

Radiux dan FreeRADIUS berbagi satu database PostgreSQL yang sama. FreeRADIUS membaca tabel standar (`radcheck`, `radreply`, `radgroupcheck`, `radgroupreply`, `radacct`, `nas`, dll) langsung lewat modul SQL-nya, sehingga setiap perubahan user/paket dari Radiux langsung aktif tanpa perlu restart service. Untuk aksi real-time seperti **Disconnect** atau **Change of Authorization (CoA)**, Radiux memiliki RADIUS client sendiri yang mengirim paket sesuai RFC 5176 langsung ke NAS, dengan mapping atribut per vendor agar kompatibel lintas merk perangkat. Detail lengkap ada di `PLAN.md` bagian 2.

## Prasyarat

- Docker Engine & Docker Compose v2
- Git
- Minimal 2 vCPU / 2GB RAM (rekomendasi produksi: 4 vCPU / 4GB RAM ke atas, tergantung jumlah NAS & user aktif)

## Instalasi (Quick Start)

Seluruh dependensi (Python packages via `uv`, FreeRADIUS, PostgreSQL, Redis) terinstal otomatis lewat image Docker — tidak perlu instalasi manual di host.

```bash
git clone https://github.com/chrisnadhe/radiux.git
cd radiux
cp .env.example .env
# sesuaikan kredensial DB, secret key, dan RADIUS shared secret default di .env

docker compose up -d --build
```

Setelah container berjalan, jalankan migrasi database dan buat akun superadmin awal:

```bash
docker compose exec app uv run alembic upgrade head
docker compose exec app uv run python -m radiux.cli create-superadmin
```

Akses dashboard di `http://localhost:8000` (atau domain yang dikonfigurasi di reverse proxy).

## Konfigurasi (.env)

| Variabel | Keterangan |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Kredensial database bersama (Radiux + FreeRADIUS) |
| `SECRET_KEY` | Secret untuk session/JWT admin Radiux |
| `RADIUS_DEFAULT_SECRET` | Shared secret default untuk NAS baru |
| `REDIS_URL` | Koneksi Redis untuk background job & cache |
| `SMTP_*` / `WA_GATEWAY_*` | (opsional) kredensial notifikasi email/WhatsApp |

## Struktur Proyek

```
radiux/
├── app/
│   ├── api/                # FastAPI routers
│   ├── core/                # config, security, dependencies
│   ├── models/              # SQLAlchemy models (radius + radiux extension)
│   ├── services/            # business logic (billing, coa, accounting)
│   ├── radius/               # RADIUS client (pyrad) untuk CoA/Disconnect
│   ├── templates/            # Jinja2 + HTMX partials
│   └── static/                # Tailwind output, JS minimal
├── freeradius/
│   ├── mods-config/sql/      # konfigurasi rlm_sql
│   └── dictionary.vendor/    # dictionary per vendor NAS
├── migrations/                # Alembic
├── docker/                    # Dockerfile per service
├── docker-compose.yml
├── pyproject.toml
└── PLAN.md
```

## Development Lokal (tanpa Docker, opsional)

```bash
uv venv
uv sync
uv run uvicorn app.main:app --reload
```

Untuk FreeRADIUS & PostgreSQL tetap disarankan jalan via Docker meski backend di-develop lokal, agar konsisten dengan environment produksi.

## Roadmap

Lihat [`PLAN.md`](./PLAN.md) untuk roadmap fase pengembangan lengkap, skema database, dan strategi deployment.

## Lisensi

Proyek ini dilisensikan di bawah **Lisensi MIT** — lihat file [`LICENSE`](./LICENSE) untuk detail selengkapnya.

## Kontribusi

Repo masih tahap awal pengembangan. Panduan kontribusi akan ditambahkan setelah struktur dasar (Phase 0) selesai.
