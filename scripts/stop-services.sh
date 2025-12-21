#!/bin/bash
# Stop all services

set -e

echo "Stopping all services..."

docker-compose down

echo "Services stopped!"
