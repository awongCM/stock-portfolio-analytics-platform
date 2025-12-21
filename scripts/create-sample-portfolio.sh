#!/bin/bash
set -e

echo "Creating sample portfolio..."

docker cp scripts/create-sample-portfolio.py portfolio-spark:/tmp/create_portfolio.py
docker exec portfolio-spark python /tmp/create_portfolio.py

echo "Portfolio creation complete!"
