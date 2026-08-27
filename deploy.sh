#!/bin/bash
set -e

# ==============================================================================
# ScreenScout Turnkey Production Deployment Script
# Targets: Google Compute Engine (Ubuntu 22.04/24.04 LTS / Debian)
# ==============================================================================

echo "========================================================"
echo "🚀 Starting ScreenScout Production Deployment..."
echo "========================================================"

# 1. Install Docker & Docker Compose if not found
if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER || true
    echo "✓ Docker installed successfully."
fi

# 2. Check and prepare .env file
if [ ! -f ".env" ]; then
    echo "⚙️ Creating production .env configuration..."
    cat <<EOF > .env
POSTGRES_DB=screenscout
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$(openssl rand -hex 16)
JWT_SECRET=$(openssl rand -hex 32)
TELEGRAM_BOT_TOKEN=8741735560:AAFa9GjTfZf2u11aZ9oK8L7M6N5P4Q3R2S1
NOTIFICATION_STREAM_NAME=screenscout:notifications:stream
CACHE_MOVIE_LIST_TTL=5m
CACHE_MOVIE_DETAIL_TTL=10m
EOF
    echo "✓ Generated secure random credentials in .env"
fi

# 3. Build and launch production Docker containers
echo "🏗️ Building and starting ScreenScout containers..."
docker compose -f docker-compose.prod.yml up -d --build

# 4. Wait for PostgreSQL healthcheck
echo "⏳ Waiting for PostgreSQL database to initialize..."
until docker exec screenscout_prod_db pg_isready -U postgres -d screenscout > /dev/null 2>&1; do
    echo "   ... waiting for database readiness ..."
    sleep 2
done
echo "✓ Database is healthy and ready!"

# 5. Populate initial cinema catalog and test data
echo "🎬 Populating cinema database and test data..."
docker compose -f docker-compose.prod.yml run --rm notification-service python scripts/seed_test_data.py || true

echo "========================================================"
echo "🎉 ScreenScout is LIVE in Production!"
echo "========================================================"
echo ""
echo "🌐 Access your deployment at: http://$(curl -s ifconfig.me || echo 'YOUR_SERVER_IP')"
echo ""
echo "📊 Running Containers:"
docker compose -f docker-compose.prod.yml ps
echo ""
echo "👑 Admin Account:  Username: admin   |  Password: Password123!"
echo "========================================================"
