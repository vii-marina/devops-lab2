#!/usr/bin/env bash
# Automatic backup script:
# - Creates tar.gz archive of given directory
# - Adds timestamp to archive name
# - Logs all actions to log file
# - Keeps only last 5 backups (oldest are removed)
#
# Usage:
#   ./backup.sh SOURCE_DIR BACKUP_DIR
#
# Example:
#   ./backup.sh /home/user/my_project /home/user/backups

set -euo pipefail

MAX_BACKUPS=5

usage() {
    echo "Usage: $0 SOURCE_DIR BACKUP_DIR" >&2
    exit 1
}

# Check arguments
if [ "$#" -ne 2 ]; then
    usage
fi

SRC_DIR="$1"
DEST_DIR="$2"

# Validate source directory
if [ ! -d "$SRC_DIR" ]; then
    echo "ERROR: Source directory '$SRC_DIR' does not exist." >&2
    exit 1
fi

# Create destination directory if it does not exist
mkdir -p "$DEST_DIR"

# Prepare names
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
SRC_BASENAME="$(basename "$SRC_DIR")"
BACKUP_FILENAME="backup_${SRC_BASENAME}_${TIMESTAMP}.tar.gz"
BACKUP_PATH="${DEST_DIR}/${BACKUP_FILENAME}"
LOG_FILE="${DEST_DIR}/backup.log"

log() {
    local msg="$1"
    local now
    now="$(date +'%Y-%m-%d %H:%M:%S')"
    echo "[$now] $msg" | tee -a "$LOG_FILE"
}

log "=== Backup started for '$SRC_DIR' ==="

# Create archive
log "Creating archive: $BACKUP_PATH"

PARENT_DIR="$(dirname "$SRC_DIR")"
DIR_NAME="$(basename "$SRC_DIR")"

if tar -czf "$BACKUP_PATH" -C "$PARENT_DIR" "$DIR_NAME" >>"$LOG_FILE" 2>&1; then
    log "Archive created successfully."
else
    log "ERROR: tar command failed."
    exit 1
fi

# Cleanup old backups: keep only last MAX_BACKUPS
log "Checking for old backups to remove (keep last ${MAX_BACKUPS})."

backup_pattern="${DEST_DIR}/backup_${SRC_BASENAME}_"*.tar.gz

# Отримуємо список backup'ів (найновіші першими) у вигляді тексту
backups_list="$(ls -1t $backup_pattern 2>/dev/null || true)"

if [ -z "$backups_list" ]; then
    log "No backups found for cleanup."
    log "Backup finished successfully."
    exit 0
fi

# Порахуємо кількість файлів
backup_count="$(printf '%s\n' "$backups_list" | wc -l | tr -d ' ')"

if [ "$backup_count" -le "$MAX_BACKUPS" ]; then
    log "No old backups to remove. Total backups: $backup_count"
else
    to_remove=$((backup_count - MAX_BACKUPS))
    log "Found $backup_count backups, removing $to_remove oldest."

    # В списку найновіші зверху, найстаріші знизу.
    # Беремо останні to_remove рядків (це найстаріші backup'и) і видаляємо їх.
    printf '%s\n' "$backups_list" | tail -n "$to_remove" | while read -r old_backup; do
        log "Removing old backup: $old_backup"
        rm -f "$old_backup" || log "WARNING: Failed to remove $old_backup"
    done
fi

log "Backup finished successfully."
exit 0

