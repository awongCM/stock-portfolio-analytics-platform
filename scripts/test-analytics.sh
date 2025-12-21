#!/bin/bash
set -e

echo "Testing analytics modules..."

docker cp scripts/test-analytics.py portfolio-spark:/tmp/test_analytics.py
docker exec portfolio-spark python /tmp/test_analytics.py

echo "Analytics test complete!"
