#!/usr/bin/env bash
# ==============================================================================
# ScreenScout Log Rotation & 30-Day Retention Enforcer
# ==============================================================================
# Manages rotation, gzip compression, and 30-day retention of ScreenScout logs.
# Can run as a standalone cron task or inside the daily 2:00 AM maintenance job.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
ARCHIVE_DIR="${LOG_DIR}/archive"

export TZ="Asia/Singapore"
RETENTION_DAYS=30

mkdir -p "${LOG_DIR}" "${ARCHIVE_DIR}"

log_msg() {
    printf "[log_rotation] %s\n" "$1"
}

log_msg "Starting 30-day log rotation and retention check..."

# 1. Rotate active primary log files if non-empty
ACTIVE_LOGS=("fetch_pipeline.log" "subscription_monitor.log" "db_cleanup.log")
TODAY_TAG=$(TZ="Asia/Singapore" date +"%Y%m%d_%H%M%S")

for log_name in "${ACTIVE_LOGS[@]}"; do
    current_file="${LOG_DIR}/${log_name}"
    if [ -f "${current_file}" ] && [ -s "${current_file}" ]; then
        base_name="${log_name%.log}"
        rotated_file="${ARCHIVE_DIR}/${base_name}_${TODAY_TAG}.log"
        
        # Copy and truncate atomically to prevent dropping in-flight writes
        cp "${current_file}" "${rotated_file}"
        : > "${current_file}"
        
        log_msg "Rotated '${log_name}' -> 'archive/${base_name}_${TODAY_TAG}.log'"
    fi
done

# 2. Compress uncompressed archives with gzip
COMPRESSED_COUNT=0
for uncompressed in "${ARCHIVE_DIR}"/*.log; do
    if [ -f "${uncompressed}" ]; then
        gzip -f "${uncompressed}"
        COMPRESSED_COUNT=$(( COMPRESSED_COUNT + 1 ))
    fi
done

if [ ${COMPRESSED_COUNT} -gt 0 ]; then
    log_msg "Compressed ${COMPRESSED_COUNT} archived log file(s) with gzip."
fi

# 3. Purge archives older than RETENTION_DAYS (30 days)
PURGED_COUNT=0
if command -v find >/dev/null 2>&1; then
    # Find all archives modified more than 30 days ago
    while IFS= read -r old_file; do
        if [ -n "${old_file}" ] && [ -f "${old_file}" ]; then
            rm -f "${old_file}"
            log_msg "Purged expired log archive (> ${RETENTION_DAYS} days): $(basename "${old_file}")"
            PURGED_COUNT=$(( PURGED_COUNT + 1 ))
        fi
    done < <(find "${ARCHIVE_DIR}" -type f \( -name "*.log.gz" -o -name "*.log" \) -mtime +${RETENTION_DAYS} 2>/dev/null)
fi

log_msg "Log rotation complete. (Purged ${PURGED_COUNT} archive files older than ${RETENTION_DAYS} days)"
