#!/bin/bash
# Start all services with automatic initialization

set -e

echo "=========================================="
echo "Starting Portfolio Analytics Platform"
echo "=========================================="

# Preflight: Supabase Studio bind mount + env file
mkdir -p supabase/snippets
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# Start Docker Compose services
echo "Starting Docker services..."
docker-compose up -d --build

# Start Supabase CLI
echo "Starting Supabase services..."
supabase start -x vector

echo ""
echo "Waiting for services to initialize..."
echo "This may take 1-2 minutes on first run..."
echo ""

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo " ✓"

# Wait for MinIO
echo -n "Waiting for MinIO..."
until curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo " ✓"

# Wait for Spark/Jupyter
echo -n "Waiting for Jupyter Lab..."
until curl -f http://localhost:8888/api > /dev/null 2>&1; do
  echo -n "."
  sleep 3
done
echo " ✓"

echo ""
echo "=========================================="
echo "✅ All services are ready!"
echo "=========================================="
echo ""
echo "Access points:"
echo "  📊 Jupyter Lab:    http://localhost:8888"
echo "  ⚡ Spark Master UI: http://localhost:8080"
echo "  🗄️  MinIO Console:   http://localhost:9001 (minioadmin/minioadmin)"
echo "  🐘 PostgreSQL:      localhost:5432 (postgres/postgres)"
echo "  🦜 Supabase Studio: http://localhost:54323 (postgres/postgres)"
echo ""
echo "Database Schema: ✓ Initialized"
echo "Iceberg Tables:  ✓ Created"
echo "MinIO Buckets:   ✓ Configured"
echo ""
echo "Next steps:"
echo "  1. Load sample data:      docker exec portfolio-spark python scripts/insert-sample-data.py"
echo "  2. Create sample portfolio: docker exec portfolio-spark python scripts/create-sample-portfolio.py"
echo "  3. Run analytics test:    docker exec portfolio-spark python scripts/test-analytics.py"
echo ""
