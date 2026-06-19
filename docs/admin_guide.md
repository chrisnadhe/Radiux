# Panduan Administrator Radiux

Dokumen ini adalah panduan lengkap bagi Administrator Sistem untuk memasang, mengamankan, mencadangkan, memantau, dan melakukan pemecahan masalah (*troubleshooting*) pada aplikasi **Radiux** di lingkungan produksi menggunakan Docker Compose.

---

## Daftar Isi
1. [Prasyarat & Port Jaringan](#prasyarat--port-jaringan)
2. [Konfigurasi SSL Lokal & HTTPS Nginx](#konfigurasi-ssl-lokal--https-nginx)
3. [Manajemen Backup & Restore Database](#manajemen-backup--restore-database)
4. [Integrasi Monitoring (Prometheus & Grafana)](#integrasi-monitoring-prometheus--grafana)
5. [Troubleshooting & Perintah Administrasi (CLI)](#troubleshooting--perintah-administrasi-cli)

---

## Prasyarat & Port Jaringan

### Prasyarat Sistem Minimum
*   **CPU**: 2 vCPU atau lebih.
*   **RAM**: Minimal 2 GB (Rekomendasi 4 GB untuk produksi dengan ribuan user).
*   **Penyimpanan**: SSD minimal 20 GB (tergantung volume log audit dan accounting).
*   **Sistem Operasi**: Linux (Ubuntu 22.04 LTS atau sejenisnya) dengan Docker Engine dan Docker Compose v2 terpasang.

### Port Jaringan yang Harus Dibuka
Untuk memastikan sistem berfungsi penuh, buka port-port berikut pada firewall server Anda:

| Port | Protokol | Sumber/Tujuan | Deskripsi |
|---|---|---|---|
| **80** | TCP | Publik | HTTP (otomatis diarahkan ke HTTPS) |
| **443** | TCP | Publik | HTTPS (Akses Web UI Radiux & Grafana) |
| **1812** | UDP | Router NAS | Autentikasi RADIUS (*Auth*) |
| **1813** | UDP | Router NAS | Akuntansi RADIUS (*Acct*) |
| **3799** | UDP | Router NAS | Port CoA / Disconnect (dikirim dari server ke NAS) |

> [!CAUTION]
> Jangan pernah membuka port database PostgreSQL (**5432**) atau Redis (**6379**) ke publik. Port-port ini harus diisolasi di dalam jaringan internal Docker (`radiux_net`).

---

## Konfigurasi SSL Lokal & HTTPS Nginx

Radiux dirancang untuk berjalan dengan HTTPS demi keamanan transfer token dan data pelanggan. Pada setup default produksi (`docker-compose.prod.yml`), Nginx dikonfigurasi menggunakan sertifikat SSL lokal (Self-Signed).

### Cara Kerja SSL Otomatis (`ssl-init`)
1.  Saat perintah `docker compose` pertama kali dijalankan, container `ssl-init` akan berjalan lebih dulu.
2.  Container ini menggunakan utilitas `openssl` untuk mengecek apakah file sertifikat sudah ada di volume `nginx_ssl`.
3.  Jika belum ada (`nginx.crt` dan `nginx.key`), sistem otomatis men-generate sertifikat self-signed yang berlaku selama 10 tahun (3650 hari).
4.  Setelah generator selesai, container `ssl-init` akan berhenti secara aman (`completed successfully`), lalu container `nginx` utama akan menyala dan membaca sertifikat tersebut.

### HTTPS Redirection
Konfigurasi Nginx (`docker/nginx/nginx.conf`) otomatis mengalihkan semua lalu lintas HTTP (port 80) ke HTTPS (port 443):
```nginx
server {
    listen 80;
    server_name _;
    location / {
        return 301 https://$host$request_uri;
    }
}
```

### Menggunakan Sertifikat SSL Tepercaya (Opsional)
Jika Anda ingin mengganti sertifikat self-signed dengan sertifikat tepercaya (seperti Let's Encrypt atau SSL berbayar):
1.  Salin file `.crt` dan `.key` milik domain Anda ke server.
2.  Timpa file di dalam volume Docker `nginx_ssl` yang berada di direktori data Docker server Anda, ATAU ubah konfigurasi bind mount di `docker-compose.prod.yml` pada bagian service `nginx` untuk menunjuk langsung ke file sertifikat Anda di host.
3.  Restart container Nginx:
    ```bash
    docker compose restart nginx
    ```

---

## Manajemen Backup & Restore Database

Database PostgreSQL menyimpan semua konfigurasi pengguna, voucher, tenant, audit log, dan data histori sesi. Backup berkala wajib dilakukan.

### 1. Backup Database
Gunakan script `scripts/backup.sh` yang telah disediakan. Script ini akan melakukan dump database PostgreSQL langsung dari container dan mengompresnya menjadi file `.sql.gz` di dalam folder `./backups`.

Jalankan backup manual:
```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```
File cadangan akan disimpan dengan format nama: `backups/radiux_backup_YYYYMMDD_HHMMSS.sql.gz`.

### 2. Otomatisasi Backup via Cronjob
Untuk melakukan backup otomatis setiap hari pada pukul 02:00 pagi:
1.  Buka tab editor cron di server host Anda:
    ```bash
    crontab -e
    ```
2.  Tambahkan baris berikut di bagian akhir file (sesuaikan path absolut direktori proyek Radiux Anda):
    ```cron
    0 2 * * * cd /home/ubuntu/radiux && ./scripts/backup.sh >> ./backups/backup.log 2>&1
    ```
3.  Simpan dan keluar.

### 3. Restore Database
> [!WARNING]
> Proses restore akan menimpa dan menghapus seluruh data yang ada di database saat ini. Pastikan Anda memilih file backup yang tepat.

Jalankan script restore dengan menyertakan path file backup sebagai argumen:
```bash
chmod +x scripts/restore.sh
./scripts/restore.sh backups/radiux_backup_20260619_075000.sql.gz
```
Ketik `y` atau `Y` saat konfirmasi untuk melanjutkan proses penulisan ulang database.

---

## Integrasi Monitoring (Prometheus & Grafana)

Radiux dilengkapi dengan sistem monitoring bawaan untuk memantau beban sistem, penggunaan database, statistik FreeRADIUS, serta visualisasi metrik performa.

### Cara Mengakses Monitoring
1.  Buka browser Anda dan akses alamat server dengan sub-path `/grafana/` (misalnya: `https://ip-server-anda/grafana/`).
2.  Masukkan kredensial login default Grafana:
    *   **Username**: `admin`
    *   **Password**: Sesuai dengan nilai `GRAFANA_ADMIN_PASSWORD` di `.env` (jika kosong, default-nya adalah `admin`).
3.  Ubah password default pada saat pertama kali login demi keamanan.

### Struktur Pemantauan
*   **Prometheus**: Bertindak sebagai *time-series database* yang melakukan *scraping* metrik dari aplikasi backend FastAPI (pada endpoint `/metrics`) setiap 15 detik.
*   **Grafana**: Menampilkan visualisasi data dari datasource Prometheus secara real-time. Dashboard bawaan disediakan di folder `./docker/grafana/provisioning/dashboards/` untuk memantau metrik performa FastAPI.

---

## Troubleshooting & Perintah Administrasi (CLI)

### 1. Membaca Log Docker
Jika terjadi kejanggalan sistem (misal: halaman web lambat atau router tidak bisa autentikasi), periksa log container dengan perintah berikut:

*   **Melihat Log Semua Service**:
    ```bash
    docker compose logs -f
    ```
*   **Melihat Log Aplikasi Backend**:
    ```bash
    docker compose logs -f app
    ```
*   **Melihat Log FreeRADIUS**:
    ```bash
    docker compose logs -f freeradius
    ```

### 2. Uji Konektivitas Autentikasi RADIUS (`radtest`)
Untuk menguji apakah engine FreeRADIUS berjalan dengan baik dan database `rlm_sql` terhubung tanpa perlu menguji menggunakan router fisik:
1.  Masuk ke dalam container `freeradius`:
    ```bash
    docker compose exec freeradius sh
    ```
2.  Kirim paket pengujian autentikasi menggunakan perintah `radtest` (ganti `username`, `password`, dan `shared_secret` sesuai data Anda):
    ```bash
    # Format: radtest <username> <password> localhost 0 <shared_secret>
    radtest testuser testpassword localhost 0 testing123
    ```
3.  Jika menerima balasan `Access-Accept`, berarti RADIUS server berfungsi dengan sempurna. Jika `Access-Reject` atau `No reply`, periksa database server dan kecocokan shared secret.

### 3. Membuat Akun Superadmin Baru via CLI
Jika Anda kehilangan akses ke akun superadmin atau baru pertama kali memasang aplikasi, Anda bisa membuat akun superadmin baru secara interaktif langsung dari dalam container aplikasi:
```bash
docker compose exec app uv run python -m app.cli create-superadmin
```
Masukkan username, email, password, dan konfirmasi password sesuai instruksi interaktif yang tampil di layar.
