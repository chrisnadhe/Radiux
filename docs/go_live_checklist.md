# Go-Live Checklist Radiux

Dokumen ini adalah daftar periksa (*checklist*) langkah demi langkah yang wajib dilewati sebelum meluncurkan sistem Radiux ke lingkungan produksi (*go-live*).

---

## Daftar Periksa Go-Live

### 1. Keamanan & Kredensial
- [ ] **Ubah Kredensial Database**: Pastikan nilai `POSTGRES_PASSWORD` di `.env` telah diganti dengan kata sandi acak yang kuat. Jangan gunakan password default (`radiux_pass`).
- [ ] **Ganti Secret Key JWT**: Pastikan parameter `SECRET_KEY` di `.env` telah diisi dengan string acak dengan entropi tinggi (buat menggunakan `openssl rand -hex 32`).
- [ ] **Konfigurasi RADIUS Default Secret**: Ganti `RADIUS_DEFAULT_SECRET` di `.env` dengan password default yang kuat untuk mendaftarkan NAS baru.
- [ ] **Ubah Password Admin Grafana**: Buka Grafana di `/grafana/` dan ubah password administrator dari `admin` ke password yang aman, atau set `GRAFANA_ADMIN_PASSWORD` di `.env` sebelum menyalakan container.
- [ ] **Buat Akun Superadmin Baru**: Buat akun superadmin riil melalui command-line interface (CLI) dan hapus akun pengujian/dummy (jika ada) demi mencegah akses tidak sah.

---

### 2. Jaringan & Firewall
- [ ] **Konfigurasi Firewall Host (misal: UFW/iptables)**:
  - [ ] Izinkan akses port **80** dan **443** TCP untuk lalu lintas web (HTTP/HTTPS).
  - [ ] Izinkan akses port **1812** dan **1813** UDP hanya dari alamat IP/subnet router NAS Anda. Jangan buka port RADIUS ke seluruh internet.
  - [ ] Blokir akses port **5432** TCP (Postgres) dan **6379** TCP (Redis) dari luar host.
- [ ] **Verifikasi IP Binding**: Pastikan konfigurasi IP di Docker Compose atau Nginx terikat pada interface jaringan yang benar (lokal/publik).
- [ ] **Uji Jalur CoA (Port 3799 UDP)**: Pastikan server Radiux diizinkan untuk mengirim paket UDP ke port 3799 pada router NAS guna melakukan operasi kick user (*Disconnect-Request*).

---

### 3. Integrasi Notifikasi
- [ ] **Konfigurasi Server SMTP**: Isi parameter email SMTP di `.env` (host, port, username, password, sender address) dan lakukan uji kirim email (misal: notifikasi pendaftaran).
- [ ] **Konfigurasi WhatsApp Gateway (Opsional)**: Verifikasi endpoint URL dan token API WhatsApp Gateway Anda di `.env`.
- [ ] **Konfigurasi Telegram Bot (Opsional)**: Pastikan token Bot Telegram dan target Chat ID telah terisi dengan benar.

---

### 4. Pemantauan & Disk Space
- [ ] **Log Rotation Aktif**: Pastikan opsi `logging` dengan `max-size: "50m"` dan `max-file` sudah aktif di setiap service pada `docker-compose.prod.yml` untuk mencegah disk penuh karena file log.
- [ ] **Verifikasi Dashboard Grafana**: Masuk ke Grafana dan pastikan panel visualisasi dapat memuat metrik CPU, memori, dan performa dari Prometheus secara normal.
- [ ] **Jadwal Backup Otomatis**: Pastikan cronjob untuk `./scripts/backup.sh` telah terpasang dan log backup berjalan tanpa error.
- [ ] **Uji Script Restore**: Sebelum go-live, jalankan skenario simulasi pemulihan data menggunakan script `./scripts/restore.sh` untuk memastikan cadangan dapat dibaca dengan sukses.

---

### 5. Validasi Fungsionalitas Akhir
- [ ] **Uji Autentikasi (`radtest`)**: Lakukan simulasi autentikasi user PPPoE/Hotspot menggunakan utilitas `radtest` dari container `freeradius` untuk memvalidasi integrasi database.
- [ ] **Uji Generate Voucher**: Lakukan pembuatan 1 batch voucher di panel Reseller dan pastikan file PDF voucher terbuat dengan layout yang benar dan QR code terbaca.
- [ ] **Uji Operasi CoA (Kick)**: Hubungkan satu router NAS uji coba, jalankan sesi koneksi pelanggan, lalu tekan tombol **Disconnect** pada panel. Pastikan sesi pelanggan pada router terputus seketika.
