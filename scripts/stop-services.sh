#!/bin/bash
# Stop all services

set -e

echo "Stopping all services..."

docker-compose down
supabase stop

echo "Services stopped!"
