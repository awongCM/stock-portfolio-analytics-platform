#!/bin/bash
# Database initialization script that runs automatically after PostgreSQL is ready

set -e

echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=postgres psql -h localhost -U postgres -d portfolio -c '\q' 2>/dev/null; do
  sleep 2
done

echo "PostgreSQL is ready!"
echo "Database schema will be initialized automatically via migrations in /docker-entrypoint-initdb.d"
