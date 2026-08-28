# ScreenScout

The most reliable movie aggregation platform in Singapore capable of providing real-time movie availability information across all major cinema operators such as Golden Village and Shaw Theatre.

## Quick Start & Task Automation

ScreenScout provides a `Makefile`, Docker Compose services, and a `./run.sh` script so you can execute tasks locally or in Docker.

### Available Commands

| Command | Local Execution | Docker Compose Command | Description |
| :--- | :--- | :--- | :--- |
| **Show Menu** | `make help` | `./run.sh help` | Display menu of available commands |
| **Setup Env** | `make setup` | N/A | Create virtual environment & install Playwright browser |
| **Start Database** | `make db-up` | `docker compose up -d postgres` | Start PostgreSQL container in background |
| **Stop Database** | `make db-down` | `docker compose down` | Stop PostgreSQL container |
| **Database Logs** | `make db-logs` | `docker compose logs -f postgres` | View real-time PostgreSQL database container logs |
| **Interactive PSQL**| `make db-psql` | `docker compose exec postgres psql ...` | Open interactive PostgreSQL shell |
| **Scrape Cinemas** | `make scrape-cinemas` | `docker compose run --rm scrape-cinemas` | Scrape cinema locations (GV & Shaw) |
| **Scrape Movies** | `make scrape-movies` | `docker compose run --rm scrape-movies` | Scrape movies and schedules (GV & Shaw) |
| **Scrape GV** | `make scrape-gv` | `docker compose run --rm scrape-gv` | Scrape cinemas, movies, and schedules for **Golden Village** |
| **Scrape Shaw** | `make scrape-shaw` | `docker compose run --rm scrape-shaw` | Scrape cinemas, movies, and schedules for **Shaw Theatre** |
| **Clean Database** | `make clean-db` | `docker compose run --rm clean-db` | Remove expired showtime schedules and outdated movies |
| **Run Pipeline** | `make run-all` | `docker compose run --rm run-all` | Run full pipeline (Start DB -> Scrape -> Clean) |

### Usage Examples

#### Option 1: Using Makefile / `./run.sh` (Recommended)
```bash
# Start DB & run Golden Village scraper locally
make db-up
make scrape-gv

# Or run via Docker containers
make docker-scrape-gv
```

#### Option 2: Using Docker Compose Directly
```bash
# Start PostgreSQL database
docker compose up -d postgres

# Run Golden Village scraper container
docker compose run --rm scrape-gv

# Run Shaw Theatre scraper container
docker compose run --rm scrape-shaw

# Run full end-to-end pipeline in Docker
## Production Linux Cron Jobs & Automated Logging

ScreenScout comes with turnkey Linux cron automation with **Singapore Timezone (SGT / Asia/Singapore / UTC+8)** logging and **30-day log rotation**.

### Scheduled Cron Tasks

| Frequency | Task | Description |
| :--- | :--- | :--- |
| `0 */6 * * *` | **Full Fetch Pipeline** | Scrapes cinemas, movies, and schedules across all providers |
| `*/5 * * * *` | **Subscription Monitor** | Checks active subscriptions and dispatches Telegram notifications |
| `0 2 * * *` | **Daily Cleanup & Rotation** | Cleans expired schedules/movies and enforces 30-day log rotation |

### Installation & Management

```bash
# 1. Install cron jobs into current user crontab
make cron-setup
# or: ./scripts/setup_cron.sh

# 2. View installed crontab and log file status
make cron-status

# 3. Stream live logs across all cron tasks
make cron-logs

# 4. Remove cron jobs
make cron-remove
```

### Log File Locations
- **Fetch Pipeline:** `logs/fetch_pipeline.log`
- **Subscription Monitor:** `logs/subscription_monitor.log`
- **Daily Cleanup:** `logs/db_cleanup.log`
- **Gzip Archives (30 Days Retention):** `logs/archive/`
