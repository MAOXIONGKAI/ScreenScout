.PHONY: help setup db-up db-down db-logs db-psql scrape-cinemas scrape-movies scrape-gv scrape-shaw clean-db run-all docker-scrape-cinemas docker-scrape-movies docker-scrape-gv docker-scrape-shaw docker-clean-db docker-run-all

PYTHON := $(shell if [ -f venv/bin/python ]; then echo "venv/bin/python"; else echo "python3"; fi)

help: ## Show this help message
	@echo "\033[1;33mScreenScout Command Runner\033[0m"
	@echo ""
	@echo "Usage: make \033[36m<target>\033[0m"
	@echo ""
	@echo "Available targets (Local Execution):"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -v 'docker-' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Available targets (Docker Execution):"
	@grep -E '^docker-[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

setup: ## Set up Python virtualenv and install dependencies
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	./venv/bin/playwright install chromium

db-up: ## Start PostgreSQL database container in background
	docker compose up -d postgres

db-down: ## Stop PostgreSQL database container
	docker compose down

db-logs: ## View PostgreSQL database container logs
	docker compose logs -f postgres

db-psql: ## Open interactive psql shell inside database container
	docker compose exec postgres psql -U postgres -d screenscout

scrape-cinemas: ## Scrape and store cinema locations (Golden Village & Shaw)
	$(PYTHON) movie_scraping/cinemas/main.py

scrape-movies: ## Scrape and store movies and showtime schedules (Golden Village & Shaw)
	$(PYTHON) movie_scraping/cinemas/main.py
	$(PYTHON) movie_scraping/movies_and_schedules/main.py

scrape-gv: ## Scrape cinemas, movies, and schedules for Golden Village only
	$(PYTHON) movie_scraping/cinemas/main.py --provider gv
	$(PYTHON) movie_scraping/movies_and_schedules/main.py --provider gv

scrape-shaw: ## Scrape cinemas, movies, and schedules for Shaw Theatre only
	$(PYTHON) movie_scraping/cinemas/main.py --provider shaw
	$(PYTHON) movie_scraping/movies_and_schedules/main.py --provider shaw

clean-db: ## Clean expired schedules and outdated movies from database
	$(PYTHON) movie_scraping/clean/main.py

run-all: db-up ## Run full pipeline locally: start DB, scrape cinemas, scrape movies/schedules, clean DB
	$(PYTHON) movie_scraping/cinemas/main.py
	$(PYTHON) movie_scraping/movies_and_schedules/main.py
	$(PYTHON) movie_scraping/clean/main.py

docker-scrape-cinemas: ## [Docker] Scrape cinema locations inside Docker container
	docker compose run --rm scrape-cinemas

docker-scrape-movies: ## [Docker] Scrape movies and schedules inside Docker container
	docker compose run --rm scrape-movies

docker-scrape-gv: ## [Docker] Scrape Golden Village inside Docker container
	docker compose run --rm scrape-gv

docker-scrape-shaw: ## [Docker] Scrape Shaw Theatre inside Docker container
	docker compose run --rm scrape-shaw

docker-clean-db: ## [Docker] Clean database inside Docker container
	docker compose run --rm clean-db

docker-run-all: ## [Docker] Run full pipeline inside Docker container
	docker compose run --rm run-all
