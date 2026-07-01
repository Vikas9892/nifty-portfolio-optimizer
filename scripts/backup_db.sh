#!/bin/sh
# ── Daily database backup ─────────────────────────────────────────────────────
# Usage (cron / Railway / Render job):
#   0 2 * * * /app/scripts/backup_db.sh
#
# For PostgreSQL: set DATABASE_URL and BACKUP_BUCKET (S3-compatible).
# For SQLite:     copies the file to BACKUP_DIR (default: /app/data/backups/).
# Keeps the last 7 daily backups and deletes older ones.

set -e

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/app/data/backups}"
mkdir -p "$BACKUP_DIR"

DATABASE_URL="${DATABASE_URL:-sqlite:///data/portfolio.db}"

echo "==> Backup started: $TIMESTAMP"

if echo "$DATABASE_URL" | grep -q "postgresql"; then
    # ── PostgreSQL ────────────────────────────────────────────────────────────
    BACKUP_FILE="$BACKUP_DIR/pg_backup_$TIMESTAMP.sql.gz"
    echo "  → PostgreSQL dump → $BACKUP_FILE"

    # Parse the DATABASE_URL
    pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"

    # Optional: upload to S3-compatible storage
    if [ -n "$BACKUP_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_BUCKET/db/$(basename "$BACKUP_FILE")"
        echo "  → Uploaded to s3://$BACKUP_BUCKET"
    fi
else
    # ── SQLite ────────────────────────────────────────────────────────────────
    # Extract the file path from sqlite:///path/to/file.db
    SQLITE_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
    BACKUP_FILE="$BACKUP_DIR/sqlite_backup_$TIMESTAMP.db.gz"

    if [ ! -f "$SQLITE_PATH" ]; then
        echo "  WARN: SQLite file not found at $SQLITE_PATH, skipping."
        exit 0
    fi

    echo "  → SQLite copy → $BACKUP_FILE"
    # Use the SQLite online backup API for a consistent snapshot
    sqlite3 "$SQLITE_PATH" ".backup '$BACKUP_DIR/tmp_backup.db'"
    gzip -c "$BACKUP_DIR/tmp_backup.db" > "$BACKUP_FILE"
    rm -f "$BACKUP_DIR/tmp_backup.db"
fi

# ── Retention: keep last 7 backups ───────────────────────────────────────────
echo "  → Pruning backups older than 7 days"
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "==> Backup complete: $BACKUP_FILE ($BACKUP_SIZE)"
