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
docker compose run --rm run-all
```
