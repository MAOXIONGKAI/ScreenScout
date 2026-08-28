#!/usr/bin/env bash
# ==============================================================================
# ScreenScout Production Cron Task Runner
# ==============================================================================
# Automatically manages execution of ScreenScout periodic tasks with:
#  - Strict Singapore Timezone (SGT / Asia/Singapore / UTC+8) logging
#  - Line-by-line timestamp prefixing: [YYYY-MM-DD HH:MM:SS SGT] [TASK] <log>
#  - Overlap protection via flock to prevent duplicate concurrent runs
#  - Automatic environment detection (Python venv vs Docker Compose)
#  - Execution duration, exit code tracking, and dedicated log persistence
# ==============================================================================

set -o pipefail

# 1. Resolve Project Root Directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# 2. Timezone and Environment Configuration
export TZ="Asia/Singapore"
export PYTHONUNBUFFERED=1

LOG_DIR="${PROJECT_ROOT}/logs"
LOCK_DIR="${PROJECT_ROOT}/.locks"
mkdir -p "${LOG_DIR}" "${LOCK_DIR}"

# 3. Load Environment Variables from .env if present
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    # Source .env without failing on syntax nuances
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.env" 2>/dev/null || true
    set +a
fi

# 4. Helper: Singapore Timestamp Generator
get_sgt_timestamp() {
    TZ="Asia/Singapore" date +"%Y-%m-%d %H:%M:%S SGT"
}

# 5. Helper: Line-by-Line Timestamp Formatter
format_stream() {
    local label="$1"
    while IFS= read -r line || [ -n "$line" ]; do
        printf "[%s] [%s] %s\n" "$(get_sgt_timestamp)" "${label}" "${line}"
    done
}

# 6. Helper: Determine Python Execution Method
resolve_python_cmd() {
    # If explicitly specified in environment
    if [ -n "${PYTHON_BIN}" ] && [ -x "${PYTHON_BIN}" ]; then
        echo "${PYTHON_BIN}"
        return 0
    fi

    # 1st preference: Project virtualenv
    if [ -x "${PROJECT_ROOT}/venv/bin/python" ]; then
        echo "${PROJECT_ROOT}/venv/bin/python"
        return 0
    fi

    # 2nd preference: Active virtualenv in PATH
    if [ -n "${VIRTUAL_ENV}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
        echo "${VIRTUAL_ENV}/bin/python"
        return 0
    fi

    # 3rd preference: System python3
    if command -v python3 >/dev/null 2>&1; then
        echo "$(command -v python3)"
        return 0
    fi

    # 4th preference: System python
    if command -v python >/dev/null 2>&1; then
        echo "$(command -v python)"
        return 0
    fi

    echo "python3"
}

# 7. Helper: Run a Python script directly or via Docker Compose
run_python_task() {
    local script_rel_path="$1"
    shift
    local args=("$@")

    local mode="${SCREENSCOUT_RUN_MODE:-auto}"

    # Auto-detect mode if not explicitly set
    if [ "${mode}" = "auto" ]; then
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "screenscout_prod_notif"; then
            mode="docker_exec"
        elif command -v docker >/dev/null 2>&1 && [ -f "${PROJECT_ROOT}/docker-compose.prod.yml" ] && docker ps --format '{{.Names}}' 2>/dev/null | grep -q "screenscout_prod_db"; then
            mode="docker_compose"
        elif [ -x "${PROJECT_ROOT}/venv/bin/python" ]; then
            mode="venv"
        else
            mode="host_python"
        fi
    fi

    case "${mode}" in
        docker_exec)
            docker exec -i screenscout_prod_notif python "${script_rel_path}" "${args[@]}"
            ;;
        docker_compose|docker)
            if [ -f "${PROJECT_ROOT}/docker-compose.prod.yml" ]; then
                docker compose -f "${PROJECT_ROOT}/docker-compose.prod.yml" run --rm notification-service python "${script_rel_path}" "${args[@]}"
            else
                docker compose run --rm scraper-base python "${script_rel_path}" "${args[@]}"
            fi
            ;;
        venv)
            "${PROJECT_ROOT}/venv/bin/python" "${PROJECT_ROOT}/${script_rel_path}" "${args[@]}"
            ;;
        host_python|*)
            local py_bin
            py_bin="$(resolve_python_cmd)"
            "${py_bin}" "${PROJECT_ROOT}/${script_rel_path}" "${args[@]}"
            ;;
    esac
}

# 8. Main Execution Wrapper
run_task() {
    local task_name="$1"
    local log_file="${LOG_DIR}/${task_name}.log"
    local lock_file="${LOCK_DIR}/${task_name}.lock"
    local start_time_sec
    start_time_sec=$(date +%s)

    # Overlap Protection (flock on Linux + PID-based check fallback)
    if command -v flock >/dev/null 2>&1; then
        exec 200>"${lock_file}"
        if ! flock -n 200; then
            local skip_msg="[$(get_sgt_timestamp)] [${task_name}] WARNING: Previous run of task '${task_name}' is still in progress. Skipping duplicate execution."
            echo "${skip_msg}" >> "${log_file}"
            echo "${skip_msg}" >&2
            return 0
        fi
    else
        if [ -f "${lock_file}" ]; then
            local lock_pid
            lock_pid=$(cat "${lock_file}" 2>/dev/null || true)
            if [ -n "${lock_pid}" ] && kill -0 "${lock_pid}" 2>/dev/null; then
                local skip_msg="[$(get_sgt_timestamp)] [${task_name}] WARNING: Previous run of task '${task_name}' (PID: ${lock_pid}) is still in progress. Skipping duplicate execution."
                echo "${skip_msg}" >> "${log_file}"
                echo "${skip_msg}" >&2
                return 0
            fi
        fi
        echo "$$" > "${lock_file}"
    fi

    # Task Header Banner
    {
        echo "================================================================================"
        echo "TASK START: ${task_name} | Host: $(hostname) | PID: $$"
        echo "Timestamp : $(get_sgt_timestamp)"
        echo "================================================================================"
    } | format_stream "${task_name}" >> "${log_file}"

    local exit_code=0

    case "${task_name}" in
        # ----------------------------------------------------------------------
        # 1. Full Scraping Pipeline (Cinemas, Movies, Schedules) - Every 6 Hours
        # ----------------------------------------------------------------------
        fetch_pipeline|scrape_all)
            {
                echo "--- Step 1/2: Scraping Cinema Locations ---"
                run_python_task "movie_scraping/cinemas/main.py"
                
                echo "--- Step 2/2: Scraping Movies & Showtime Schedules ---"
                run_python_task "movie_scraping/movies_and_schedules/main.py"
            } 2>&1 | format_stream "${task_name}" >> "${log_file}"
            exit_code=${PIPESTATUS[0]}
            ;;

        # ----------------------------------------------------------------------
        # 2. Subscription Monitor & Telegram Alerts - Every 5 Minutes
        # ----------------------------------------------------------------------
        subscription_monitor|monitor)
            {
                run_python_task "movie_scraping/monitor/subscription_checker.py"
            } 2>&1 | format_stream "${task_name}" >> "${log_file}"
            exit_code=${PIPESTATUS[0]}
            ;;

        # ----------------------------------------------------------------------
        # 3. Database Cleanup & 30-Day Log Rotation - Daily at 2:00 AM SGT
        # ----------------------------------------------------------------------
        db_cleanup|cleanup)
            {
                echo "--- Step 1/2: Cleaning Database Expired Records ---"
                run_python_task "movie_scraping/clean/main.py"

                echo "--- Step 2/2: Enforcing 30-Day Log Rotation & Archive ---"
                if [ -x "${SCRIPT_DIR}/rotate_logs.sh" ]; then
                    bash "${SCRIPT_DIR}/rotate_logs.sh"
                fi
            } 2>&1 | format_stream "${task_name}" >> "${log_file}"
            exit_code=${PIPESTATUS[0]}
            ;;

        # ----------------------------------------------------------------------
        # Custom / Ad-Hoc Command
        # ----------------------------------------------------------------------
        *)
            {
                echo "ERROR: Unknown task name '${task_name}'"
                echo "Available tasks: fetch_pipeline, subscription_monitor, db_cleanup"
            } 2>&1 | format_stream "${task_name}" >> "${log_file}"
            exit_code=1
            ;;
    esac

    local end_time_sec
    end_time_sec=$(date +%s)
    local duration=$(( end_time_sec - start_time_sec ))

    # Task Footer Banner
    {
        echo "================================================================================"
        if [ ${exit_code} -eq 0 ]; then
            echo "TASK FINISHED: ${task_name} [SUCCESS] | Duration: ${duration}s"
        else
            echo "TASK FINISHED: ${task_name} [FAILED - Exit Code ${exit_code}] | Duration: ${duration}s"
        fi
        echo "Timestamp    : $(get_sgt_timestamp)"
        echo "================================================================================"
        echo ""
    } | format_stream "${task_name}" >> "${log_file}"

    # Clean up lockfile
    rm -f "${lock_file}" 2>/dev/null || true

    return ${exit_code}
}

# 9. CLI Entrypoint
if [ $# -lt 1 ]; then
    echo "Usage: $0 <task_name>"
    echo "  Available tasks:"
    echo "    fetch_pipeline        - Full scraping pipeline (Cinemas + Movies + Schedules)"
    echo "    subscription_monitor  - Check active subscriptions & trigger Telegram alerts"
    echo "    db_cleanup            - Clean expired records & enforce 30-day log rotation"
    exit 1
fi

run_task "$1"
