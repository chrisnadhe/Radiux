# Panduan Upgrade Radiux

Dokumen ini menjelaskan langkah-langkah untuk melakukan update versi aplikasi Radiux di production.

## Prerequisites
Pastikan Anda memiliki akses SSH ke server production dan berada di direktori project Radiux.

```bash
cd /path/to/radiux
```

## Langkah-langkah Upgrade

### 1. Backup Database (Sangat Disarankan)
Sebelum melakukan pembaruan, selalu lakukan backup database untuk mencegah kehilangan data jika terjadi kegagalan migrasi.

```bash
./scripts/backup.sh
```

### 2. Tarik Kode Terbaru (Git Pull)
Ambil perubahan terbaru dari repository Git.

```bash
git pull origin main
```

### 3. Build & Restart Container Aplikasi
Lakukan build ulang untuk image aplikasi (FastAPI) agar depedensi terbaru (jika ada di `uv.lock`) ikut terinstall, kemudian restart container di background.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
> Perintah di atas secara otomatis akan mengganti container lama dengan versi baru tanpa downtime yang signifikan (rolling update secara sederhana).

### 4. Jalankan Migrasi Database (Alembic)
Jika versi terbaru memiliki perubahan skema database, Anda harus menjalankan skrip migrasi. Anda bisa menjalankannya menggunakan `docker exec` ke container `radiux_app` yang baru saja berjalan.

```bash
docker exec -t radiux_app uv run alembic upgrade head
```

### 5. Verifikasi
Periksa logs aplikasi untuk memastikan tidak ada error yang terjadi setelah upgrade.

```bash
docker logs radiux_app --tail 100 -f
```

## Rollback
Jika terjadi masalah fatal setelah upgrade, Anda bisa melakukan rollback menggunakan file backup yang sudah dibuat.

1. Kembalikan ke commit Git sebelumnya: `git checkout <commit_hash>`
2. Build dan jalankan ulang container: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
3. Restore database: `./scripts/restore.sh backups/radiux_backup_YMD_HMS.sql.gz`

