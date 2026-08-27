.PHONY: help setup db-up db-down db-logs db-psql redis-up redis-down redis-logs redis-cli scrape-cinemas scrape-movies scrape-gv scrape-shaw clean-db run-all docker-scrape-cinemas docker-scrape-movies docker-scrape-gv docker-scrape-shaw docker-clean-db docker-run-all backend frontend dev test-backend test-python test-frontend test

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

db-up: ## Start PostgreSQL and Redis containers in background
	docker compose up -d postgres redis

db-down: ## Stop PostgreSQL and Redis database containers
	docker compose down

db-logs: ## View PostgreSQL database container logs
	docker compose logs -f postgres

db-psql: ## Open interactive psql shell inside database container
	docker compose exec postgres psql -U postgres -d screenscout

redis-up: ## Start Redis container in background
	docker compose up -d redis

redis-down: ## Stop Redis container
	docker compose stop redis

redis-logs: ## View Redis container logs
	docker compose logs -f redis

redis-cli: ## Open interactive redis-cli inside Redis container
	docker compose exec redis redis-cli

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

check-subscriptions: ## Match active subscriptions against movies in DB and trigger Telegram alerts
	$(PYTHON) movie_scraping/monitor/subscription_checker.py

seed-demo: ## Populate authentic users and reviews for unreviewed movies (incremental)
	$(PYTHON) scripts/seed_demo_data.py

seed-demo-reset: ## Force wipe and re-seed all reviews from scratch
	$(PYTHON) scripts/seed_demo_data.py --reset

run-all: db-up ## Run full pipeline locally: start DB/Redis, scrape cinemas, scrape movies/schedules, clean DB, check subscriptions
	$(PYTHON) movie_scraping/cinemas/main.py
	$(PYTHON) movie_scraping/movies_and_schedules/main.py
	$(PYTHON) movie_scraping/clean/main.py
	$(PYTHON) movie_scraping/monitor/subscription_checker.py

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

notification-service: ## Start Python Notification Service on :8085
	$(PYTHON) notification_service/main.py

backend: ## Start Hertz Go backend API server on :8080
	cd backend && go run main.go

frontend: ## Start Next.js frontend dev server on :3000
	cd frontend && npm run dev

dev: db-up ## Start database, Redis, notification-service, backend, and frontend (all local)
	@echo "Starting notification service, backend and frontend..."
	@$(PYTHON) notification_service/main.py &
	@cd backend && go run main.go &
	@cd frontend && npm run dev

test-backend: ## Run Go backend unit tests
	cd backend && go test -v ./...

test-python: ## Run Python notification and monitor unit tests
	$(PYTHON) -m unittest discover -s notification_service/tests -p "test_*.py"
	$(PYTHON) -m unittest discover -s movie_scraping/tests -p "test_*.py"

test-frontend: ## Run frontend typecheck, tests, and production build
	cd frontend && npm run typecheck
	cd frontend && npm test
	cd frontend && npm run build

test: test-backend test-python test-frontend ## Run full automated test suite across Go, Python, and Frontend
