# AGENTS.md

Panduan resmi untuk **AI coding agent apa pun** (Claude Code, Cursor, GitHub Copilot, Codex CLI, Windsurf/Devin Desktop, Gemini CLI, atau lainnya) yang bekerja di repo Radiux. File ini adalah **satu-satunya sumber kebenaran (single source of truth)**. File konfigurasi khusus tool lain (`CLAUDE.md`, `GEMINI.md`, dll) tidak menduplikasi isi ini — mereka hanya menunjuk balik ke file ini, agar aturan tidak pernah berbeda antar tool/model.

Untuk konteks produk & roadmap lengkap, lihat `README.md` dan `PLAN.md`. Dokumen ini fokus ke aturan teknis praktis dan batasan perubahan saat menulis/mengubah kode.

## Ringkasan Proyek

Radiux adalah Web UI untuk mengelola FreeRADIUS (AAA, Hotspot, Billing/Voucher, Multi-Reseller) untuk ISP dengan dukungan multi-vendor NAS. Stack: FastAPI + HTMX + TailwindCSS + PostgreSQL + uv, dijalankan via Docker Compose. FreeRADIUS dan Radiux berbagi satu database PostgreSQL yang sama lewat `rlm_sql`.

## Setup & Commands

```bash
uv sync                                          # install dependency
uv run uvicorn app.main:app --reload             # dev server
docker compose up -d --build                     # semua service (app, freeradius, postgres, redis)
uv run alembic upgrade head                      # migrasi
uv run alembic revision --autogenerate -m "..."  # migrasi baru
uv run pytest                                     # test
uv run pytest -m integration                      # test integrasi (butuh docker-compose test profile)
uv run ruff check . && uv run ruff format .       # lint & format
```

Jalankan lint, format, dan test sebelum menganggap suatu task selesai.

## Konvensi Kode

- Type hints wajib di semua fungsi publik. Style ikut `ruff` default.
- Routing FastAPI dikelompokkan per domain di `app/api/v1/` (`customers.py`, `nas.py`, `billing.py`, dst) — jangan satu file untuk semua endpoint.
- Business logic wajib di `app/services/`, bukan langsung di router.
- Akses RADIUS packet (CoA/Disconnect) hanya lewat `app/radius/`.
- Penamaan tabel & kolom: `snake_case`, foreign key `<tabel_singular>_id`.

## Aturan Arsitektur yang Tidak Boleh Dilanggar

1. Jangan ubah skema tabel inti FreeRADIUS (`radcheck`, `radreply`, `radgroupcheck`, `radgroupreply`, `radusergroup`, `radacct`, `radpostauth`, `nas`). Tambahan hanya di tabel ekstensi Radiux.
2. Semua query data customer/voucher/invoice wajib di-scope `tenant_id`, termasuk dari context superadmin.
3. Shared secret NAS tidak boleh disimpan/di-log dalam bentuk plaintext.
4. CoA/Disconnect harus lewat mapping `nas_vendor_profiles`, jangan hardcode logic per vendor.
5. Data monitoring sesi aktif bersumber dari `radacct`, bukan polling langsung ke NAS.
6. Setiap create/update/delete pada data sensitif (user, paket, voucher, NAS, saldo) wajib menulis ke `audit_logs`.

## Kebijakan Perubahan Besar — Wajib Dipatuhi Semua Agent, Semua Model

Ini aturan inti dari file ini: **agent tidak boleh mengeksekusi perubahan besar tanpa konfirmasi eksplisit dari manusia**, terlepas dari model atau tool apa yang dipakai.

### Apa yang Termasuk "Perubahan Besar"

- Migrasi atau perubahan skema database apa pun (tabel inti FreeRADIUS maupun tabel ekstensi Radiux).
- Menghapus, memindahkan, atau me-rename lebih dari satu file dalam satu aksi.
- Menambah dependency baru yang signifikan, atau melakukan major version bump pada dependency yang ada.
- Refactor yang menyentuh lebih dari kurang lebih 3 file, atau yang mengubah struktur folder.
- Mengubah logic auth, RBAC, multi-tenant scoping, atau enkripsi secret.
- Mengubah file konfigurasi deployment (`docker-compose.yml`, `Dockerfile`, CI/CD).
- Mengubah keputusan arsitektur yang sudah ditetapkan di `PLAN.md` (misalnya: pendekatan integrasi FreeRADIUS, model multi-tenant, pilihan tech stack).
- Menghapus atau menulis ulang test yang sudah ada (menambah test baru tidak termasuk).

### Prosedur Wajib untuk Perubahan Besar

1. **Berhenti sebelum eksekusi** — jangan langsung jalankan perubahan.
2. **Sampaikan ringkasan**: apa yang akan diubah, alasannya, file/komponen yang terdampak, dan rencana rollback jika ada masalah.
3. **Tunggu konfirmasi eksplisit** dari manusia sebelum melanjutkan.
4. Jika tidak ada konfirmasi jelas dalam sesi yang sama, anggap **belum disetujui** — jangan eksekusi, jangan asumsikan persetujuan diam-diam.

### Perubahan Kecil (Boleh Langsung Dieksekusi)

Menambah satu endpoint baru sesuai spesifikasi yang sudah jelas, memperbaiki bug di satu file, menambah test baru, memperbaiki typo, atau menambah komentar/dokumentasi — boleh langsung dikerjakan tanpa konfirmasi tambahan, sepanjang tidak melanggar Aturan Arsitektur di atas.

### Prinsip Umum

Jika ragu apakah suatu perubahan tergolong "besar" atau "kecil", **anggap besar** dan minta konfirmasi dulu. Lebih baik bertanya lebih dulu daripada melakukan perubahan yang sulit di-rollback.

## Testing

- Unit test wajib untuk fungsi baru di `app/services/` dan `app/radius/` yang mengandung kalkulasi (billing, expiry, quota) atau pembentukan paket RADIUS.
- Integration test yang butuh FreeRADIUS/Postgres ditandai `@pytest.mark.integration`, dijalankan lewat docker-compose test profile.
- Perubahan pada CoA/Disconnect perlu test dengan emulator NAS (listener UDP sederhana), bukan hanya manual testing ke hardware fisik.

## Keamanan

- Jangan commit file `.env` atau kredensial nyata ke repo.
- Jangan bypass rate limiting yang sudah ada di endpoint auth saat menambah endpoint baru di area yang sama.
- Dependency baru ditambah lewat `uv add <package>`, jangan edit `pyproject.toml` manual tanpa sync lockfile.

## Hal yang Wajib Dikonfirmasi ke Manusia Sebelum Dikerjakan

- Apa pun yang termasuk kategori "Perubahan Besar" di atas.
- Penambahan dependency besar (framework baru, library payment gateway, dll).
- Perubahan pada model multi-tenant/RBAC yang sudah berjalan.
- Keputusan yang mengarah ke fitur akuntansi penuh untuk billing (di luar scope awal, lihat PLAN.md bagian 12).

## Catatan Lintas Tool

Tool-tool berikut membaca file ini secara otomatis tanpa konfigurasi tambahan: Cursor, GitHub Copilot, Codex CLI, Windsurf/Devin Desktop, Aider, Zed, dan agent lain yang mendukung standar AGENTS.md (Linux Foundation / Agentic AI Foundation). Untuk tool yang masih memakai nama file sendiri (Claude Code → `CLAUDE.md`, Gemini CLI → `GEMINI.md`), repo ini menyediakan file pointer singkat yang merujuk balik ke sini — lihat file-file tersebut di root repo. Jangan tambahkan aturan baru ke file pointer tersebut; semua aturan baru ditambahkan di sini agar tetap satu sumber kebenaran.
