#!/bin/bash
set -e

echo "Inserting sample stock price data..."

# Copy script to container
docker cp scripts/insert-sample-data.py portfolio-spark:/tmp/insert_sample_data.py

# Run the script
docker exec portfolio-spark python /tmp/insert_sample_data.py

echo "Sample data insertion complete!"
