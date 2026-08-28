#!/usr/bin/env bash
# ==============================================================================
# ScreenScout Turnkey Linux Cron Setup Script
# ==============================================================================
# Configures crontab on the Linux instance directly with:
#  1. Every 6 hours: Full fetch pipeline (Cinemas + Movies + Schedules)
#  2. Every 5 minutes: Subscription monitor & Telegram notification trigger
#  3. Daily at 2:00 AM SGT: Database cleanup and 30-day log rotation
#  4. Strict Singapore Timezone (SGT / Asia/Singapore / UTC+8) timestamped logging
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================================"
echo "⚙️  ScreenScout Linux Cron Setup"
echo "================================================================================"
echo "Project Root: ${PROJECT_ROOT}"
echo ""

# 1. Ensure scripts are executable
chmod +x "${SCRIPT_DIR}/cron_runner.sh" "${SCRIPT_DIR}/rotate_logs.sh" 2>/dev/null || true

# 2. Create log directories
mkdir -p "${PROJECT_ROOT}/logs/archive" "${PROJECT_ROOT}/.locks"
touch "${PROJECT_ROOT}/logs/.gitkeep"

# 3. Build Crontab Block
CRON_START_TAG="# >>> ScreenScout Cron Start >>>"
CRON_END_TAG="# <<< ScreenScout Cron End <<<"

CRON_BLOCK=$(cat <<EOF
${CRON_START_TAG}
# ScreenScout Automated Cron Jobs (Timezone: Asia/Singapore)
CRON_TZ=Asia/Singapore
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 1. Full Scraping Pipeline (Cinemas, Movies, Schedules) - Every 6 Hours (00:00, 06:00, 12:00, 18:00 SGT)
0 */6 * * * /bin/bash ${PROJECT_ROOT}/scripts/cron_runner.sh fetch_pipeline >/dev/null 2>&1

# 2. Subscription Monitor & Telegram Alerts - Every 5 Minutes
*/5 * * * * /bin/bash ${PROJECT_ROOT}/scripts/cron_runner.sh subscription_monitor >/dev/null 2>&1

# 3. Database Cleanup & 30-Day Log Rotation - Daily at 02:00 AM SGT
0 2 * * * /bin/bash ${PROJECT_ROOT}/scripts/cron_runner.sh db_cleanup >/dev/null 2>&1
${CRON_END_TAG}
EOF
)

# 4. Fetch existing crontab (filtering out any previous ScreenScout block)
EXISTING_CRON=""
if crontab -l 2>/dev/null; then
    EXISTING_CRON=$(crontab -l 2>/dev/null | awk -v start="${CRON_START_TAG}" -v end="${CRON_END_TAG}" '
        $0 ~ start { inside=1; next }
        $0 ~ end   { inside=0; next }
        !inside    { print }
    ')
fi

# 5. Combine and install updated crontab
NEW_CRONTAB=$(printf "%s\n\n%s\n" "${EXISTING_CRON}" "${CRON_BLOCK}" | sed '/^\s*$/N;/^\n$/D')

echo "${NEW_CRONTAB}" | crontab -

echo "✅ Crontab installed successfully!"
echo ""
echo "Current Installed Crontab:"
echo "--------------------------------------------------------------------------------"
crontab -l | grep -A 20 "${CRON_START_TAG}" || crontab -l
echo "--------------------------------------------------------------------------------"
echo ""

# 6. Configure System logrotate if root / sudo is available
if [ -d "/etc/logrotate.d" ]; then
    if [ "$(id -u)" -eq 0 ]; then
        echo "🔧 Installing system logrotate configuration to /etc/logrotate.d/screenscout..."
        cat <<EOF > /etc/logrotate.d/screenscout
${PROJECT_ROOT}/logs/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    create 0644 $(id -un) $(id -gn)
    dateext
    dateformat -%Y%m%d
}
EOF
        echo "✅ System logrotate installed at /etc/logrotate.d/screenscout"
    else
        echo "ℹ️  Tip: To install system logrotate with 30-day retention, run:"
        echo "   sudo cp ${SCRIPT_DIR}/logrotate.screenscout /etc/logrotate.d/screenscout"
        echo "   (Self-contained 30-day log rotation is already active in the 2:00 AM cleanup job!)"
    fi
fi

echo ""
echo "================================================================================"
echo "🎉 ScreenScout Cron Automation is READY!"
echo "================================================================================"
echo "Logs are stored with Singapore Timezone [SGT] in:"
echo "  - Fetch Pipeline : ${PROJECT_ROOT}/logs/fetch_pipeline.log"
echo "  - Monitor Alerts : ${PROJECT_ROOT}/logs/subscription_monitor.log"
echo "  - Daily Cleanup  : ${PROJECT_ROOT}/logs/db_cleanup.log"
echo "  - Log Archives   : ${PROJECT_ROOT}/logs/archive/"
echo ""
echo "Useful Commands:"
echo "  make cron-status     - Check current crontab and status"
echo "  make cron-logs       - Tail all live cron execution logs"
echo "  make cron-test       - Perform dry-run of cron jobs"
echo "================================================================================"
