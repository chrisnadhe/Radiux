#!/usr/bin/env bash
# ===========================================================================
# Radiux - Database Restore Script
# ===========================================================================

set -e

if [ -z "$1" ]; then
    echo "Penggunaan: $0 <file_backup.sql.gz>"
    echo "Contoh: $0 backups/radiux_backup_20260619_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ File $BACKUP_FILE tidak ditemukan!"
    exit 1
fi

DB_CONTAINER="radiux_postgres"
DB_USER="radiux_user"
DB_NAME="radiux_db"

echo "PERINGATAN! Ini akan me-replace seluruh data di database ${DB_NAME}."
read -p "Apakah Anda yakin ingin melanjutkan? (y/N) " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Restore dibatalkan."
    exit 0
fi

echo "Sedang melakukan restore dari $BACKUP_FILE ke container $DB_CONTAINER..."

# Extract dari gzip lalu pipe ke psql di dalam container
gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

echo "✅ Restore database berhasil!"
