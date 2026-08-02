# ScreenScout

The most reliable movie aggregation platform in Singapore capable of providing real-time movie availability information across all major cinema operators such as Golden Village and Shaw Theatre.

## Quick Start & Task Automation

ScreenScout provides a `Makefile` and `./run.sh` script so you can manage services and scrapers using simple commands.

### Available Commands

| Command | Description |
| :--- | :--- |
| `make help` or `./run.sh help` | Display interactive menu of available commands |
| `make setup` | Create virtual environment, install Python dependencies & Playwright browser |
| `make db-up` | Start PostgreSQL container in background |
| `make db-down` | Stop PostgreSQL container |
| `make db-logs` | View real-time PostgreSQL database container logs |
| `make db-psql` | Open interactive PostgreSQL shell inside container |
| `make scrape-cinemas` | Scrape and save cinema locations (Golden Village & Shaw) |
| `make scrape-movies` | Scrape and save movies and showtime schedules (Golden Village & Shaw) |
| `make scrape-gv` | Scrape cinemas, movies, and schedules for **Golden Village** only |
| `make scrape-shaw` | Scrape cinemas, movies, and schedules for **Shaw Theatre** only |
| `make clean-db` | Remove expired showtime schedules and outdated movies |
| `make run-all` | Execute complete pipeline (start DB -> scrape cinemas -> scrape movies/schedules -> clean DB) |

### Usage Examples

```bash
# 1. First-time environment setup
make setup

# 2. Start PostgreSQL database
make db-up

# 3. Scrape provider individually
make scrape-gv
make scrape-shaw

# Or run everything end-to-end
make run-all
```
