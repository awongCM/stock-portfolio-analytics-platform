#!/bin/bash
# Ingest sample stock data

set -e

echo "Ingesting sample stock data..."

# Create a temporary Python script
cat > /tmp/ingest_data.py << 'EOF'
import sys
sys.path.append('/opt/spark-apps')

from src.ingestion.stock_ingestion import StockDataIngestion
from datetime import datetime, timedelta

# Initialize ingestion
ingestion = StockDataIngestion()

# Ingest data for sample stocks
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
end_date = datetime.now().strftime('%Y-%m-%d')

print(f"Ingesting data from {start_date} to {end_date}")

results = ingestion.ingest_multiple_stocks(
    symbols=symbols,
    start_date=start_date,
    end_date=end_date
)

print("\nIngestion results:")
for symbol, count in results.items():
    print(f"  {symbol}: {count} records")

print("\nSample data ingestion complete!")
EOF

# Copy script to container and run it
docker cp /tmp/ingest_data.py portfolio-spark:/tmp/ingest_data.py
docker-compose exec -T spark python3 /tmp/ingest_data.py

# Clean up
rm /tmp/ingest_data.py

echo "Stock data ingestion complete!"
