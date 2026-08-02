FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for Playwright and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser and OS dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application source code
COPY . .

# Default database connection string for Docker Compose network
ENV DATABASE_URL=postgresql://postgres:postgres@postgres:5432/screenscout

CMD ["python", "movie_scraping/movies_and_schedules/main.py"]
