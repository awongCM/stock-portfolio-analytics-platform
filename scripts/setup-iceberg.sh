#!/bin/bash
# Initialize Iceberg tables in the catalog

set -e

echo "Setting up Apache Iceberg tables..."

# Wait for services to be ready
echo "Waiting for MinIO to be ready..."
sleep 10

# Create a temporary Python script using Spark SQL
cat > /tmp/setup_iceberg.py << 'EOF'
import sys
sys.path.append('/opt/spark-apps')

from src.iceberg.catalog import IcebergCatalog

# Initialize Spark
catalog = IcebergCatalog()
spark = catalog.get_spark_session()
catalog_name = catalog.catalog_name

print(f"Using catalog: {catalog_name}")

# Create namespace
try:
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog_name}.portfolio")
    print("✓ Created namespace: portfolio")
except Exception as e:
    print(f"Namespace creation: {e}")

TABLES = [
    "stock_prices",
    "transactions",
    "portfolio_metrics",
    "technical_indicators",
    "securities",
    "exchange_rates",
]

for table in TABLES:
    try:
        spark.sql(f"DROP TABLE IF EXISTS {catalog_name}.portfolio.{table}")
        print(f"✓ Dropped legacy table (if existed): {table}")
    except Exception as e:
        print(f"drop {table}: {e}")

# Create stock_prices table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.stock_prices (
            stock_symbol STRING,
            timestamp TIMESTAMP,
            open DECIMAL(20,6),
            high DECIMAL(20,6),
            low DECIMAL(20,6),
            close DECIMAL(20,6),
            volume BIGINT,
            adjusted_close DECIMAL(20,6),
            ingestion_timestamp TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(timestamp), stock_symbol)
    """)
    print("✓ Created table: stock_prices")
except Exception as e:
    print(f"stock_prices: {e}")

# Create transactions table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.transactions (
            transaction_id STRING,
            portfolio_id STRING,
            stock_symbol STRING,
            transaction_type STRING,
            quantity DECIMAL(20,6),
            price DECIMAL(20,6),
            commission DECIMAL(20,6),
            transaction_date TIMESTAMP,
            ingestion_timestamp TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(transaction_date), portfolio_id)
    """)
    print("✓ Created table: transactions")
except Exception as e:
    print(f"transactions: {e}")

# Create portfolio_metrics table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.portfolio_metrics (
            portfolio_id STRING,
            calculation_date TIMESTAMP,
            total_value DECIMAL(20,2),
            total_cost DECIMAL(20,2),
            realized_gains DECIMAL(20,2),
            unrealized_gains DECIMAL(20,2),
            total_return_pct DOUBLE,
            daily_return_pct DOUBLE,
            volatility DOUBLE,
            sharpe_ratio DOUBLE,
            max_drawdown_pct DOUBLE
        )
        USING iceberg
        PARTITIONED BY (days(calculation_date), portfolio_id)
    """)
    print("✓ Created table: portfolio_metrics")
except Exception as e:
    print(f"portfolio_metrics: {e}")

# Create technical_indicators table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.technical_indicators (
            stock_symbol STRING,
            timestamp TIMESTAMP,
            sma_20 DECIMAL(20,6),
            sma_50 DECIMAL(20,6),
            sma_200 DECIMAL(20,6),
            ema_12 DECIMAL(20,6),
            ema_26 DECIMAL(20,6),
            rsi_14 DOUBLE,
            macd DECIMAL(20,6),
            macd_signal DECIMAL(20,6),
            bollinger_upper DECIMAL(20,6),
            bollinger_lower DECIMAL(20,6)
        )
        USING iceberg
        PARTITIONED BY (days(timestamp), stock_symbol)
    """)
    print("✓ Created table: technical_indicators")
except Exception as e:
    print(f"technical_indicators: {e}")

# Create securities table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.securities (
            stock_symbol STRING,
            name STRING,
            exchange STRING,
            country_code STRING,
            quote_currency STRING,
            gics_sector STRING,
            gics_sector_code STRING,
            market_code STRING,
            gics_sector_override STRING,
            ingestion_timestamp TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (market_code)
    """)
    print("✓ Created table: securities")
except Exception as e:
    print(f"securities: {e}")

# Create exchange_rates table
try:
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog_name}.portfolio.exchange_rates (
            base_currency STRING,
            quote_currency STRING,
            timestamp TIMESTAMP,
            rate DOUBLE,
            ingestion_timestamp TIMESTAMP
        )
        USING iceberg
        PARTITIONED BY (days(timestamp))
    """)
    print("✓ Created table: exchange_rates")
except Exception as e:
    print(f"exchange_rates: {e}")

# Show tables
print("\nCreated tables:")
spark.sql(f"SHOW TABLES IN {catalog_name}.portfolio").show()

print("\n✓ Iceberg tables created successfully!")
EOF

# Copy script to container and run it
docker cp /tmp/setup_iceberg.py portfolio-spark:/tmp/setup_iceberg.py
docker-compose exec -T spark python3 /tmp/setup_iceberg.py

# Clean up
rm /tmp/setup_iceberg.py

echo "Iceberg setup complete!"
