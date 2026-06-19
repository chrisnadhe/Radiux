#!/usr/bin/env bash
# ===========================================================================
# Radiux - Database Backup Script
# ===========================================================================

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_CONTAINER="radiux_postgres"
DB_USER="radiux_user"
DB_NAME="radiux_db"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/radiux_backup_${TIMESTAMP}.sql.gz"

echo "Mulai backup database ${DB_NAME} dari container ${DB_CONTAINER}..."

# Jalankan pg_dump di dalam container dan compress pakai gzip
docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ -f "$BACKUP_FILE" ]; then
    echo "✅ Backup berhasil disimpan di: $BACKUP_FILE"
    echo "Ukuran file: $(ls -lh "$BACKUP_FILE" | awk '{print $5}')"
else
    echo "❌ Backup gagal!"
    exit 1
fi

# (Opsional) Rotasi backup: Hapus file lebih lama dari 30 hari
# find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +30 -exec rm {} \;
