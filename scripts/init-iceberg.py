#!/usr/bin/env python3
"""
Initialize Iceberg tables automatically after Spark is ready.
This script runs inside the Spark container on startup.
"""

import sys
import time
sys.path.append('/opt/spark-apps')

from pyspark.sql import SparkSession
from pyiceberg.catalog import load_catalog

def wait_for_minio():
    """Wait for MinIO to be ready"""
    import urllib.request
    max_retries = 30
    for i in range(max_retries):
        try:
            urllib.request.urlopen('http://minio:9000/minio/health/live', timeout=2)
            print("MinIO is ready!")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"Waiting for MinIO... ({i+1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"MinIO not ready after {max_retries} attempts")
                return False
    return False

def initialize_iceberg():
    """Initialize Iceberg catalog and tables"""
    try:
        print("Initializing Iceberg tables...")
        
        # Create Spark session with Iceberg
        spark = SparkSession.builder \
            .appName("IcebergSetup") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
            .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.iceberg.type", "hadoop") \
            .config("spark.sql.catalog.iceberg.warehouse", "s3a://iceberg-warehouse/") \
            .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
            .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
            .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .getOrCreate()
        
        # Create namespace
        spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.portfolio")
        print("✓ Namespace 'iceberg.portfolio' created")
        
        # Create stock_prices table
        spark.sql("""
            CREATE TABLE IF NOT EXISTS iceberg.portfolio.stock_prices (
                stock_id STRING,
                symbol STRING,
                timestamp TIMESTAMP,
                open DECIMAL(20, 6),
                high DECIMAL(20, 6),
                low DECIMAL(20, 6),
                close DECIMAL(20, 6),
                volume BIGINT,
                adjusted_close DECIMAL(20, 6)
            )
            USING iceberg
            PARTITIONED BY (days(timestamp), symbol)
        """)
        print("✓ Table 'stock_prices' created")
        
        # Create transactions table
        spark.sql("""
            CREATE TABLE IF NOT EXISTS iceberg.portfolio.transactions (
                transaction_id STRING,
                portfolio_id STRING,
                stock_id STRING,
                symbol STRING,
                transaction_type STRING,
                quantity DECIMAL(20, 6),
                price DECIMAL(20, 6),
                transaction_date TIMESTAMP
            )
            USING iceberg
            PARTITIONED BY (months(transaction_date))
        """)
        print("✓ Table 'transactions' created")
        
        # Create portfolio_metrics table
        spark.sql("""
            CREATE TABLE IF NOT EXISTS iceberg.portfolio.portfolio_metrics (
                portfolio_id STRING,
                metric_date DATE,
                total_value DECIMAL(20, 2),
                total_cost DECIMAL(20, 2),
                total_pnl DECIMAL(20, 2),
                return_pct DECIMAL(10, 4)
            )
            USING iceberg
            PARTITIONED BY (months(metric_date))
        """)
        print("✓ Table 'portfolio_metrics' created")
        
        # Create technical_indicators table
        spark.sql("""
            CREATE TABLE IF NOT EXISTS iceberg.portfolio.technical_indicators (
                stock_id STRING,
                symbol STRING,
                timestamp TIMESTAMP,
                sma_20 DECIMAL(20, 6),
                sma_50 DECIMAL(20, 6),
                rsi_14 DECIMAL(10, 4),
                bb_upper DECIMAL(20, 6),
                bb_middle DECIMAL(20, 6),
                bb_lower DECIMAL(20, 6)
            )
            USING iceberg
            PARTITIONED BY (days(timestamp), symbol)
        """)
        print("✓ Table 'technical_indicators' created")
        
        spark.stop()
        print("\n✅ Iceberg initialization complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing Iceberg: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting Iceberg initialization...")
    
    # Wait for MinIO
    if not wait_for_minio():
        print("Failed to connect to MinIO")
        sys.exit(1)
    
    # Initialize Iceberg
    if initialize_iceberg():
        print("Iceberg setup successful!")
        sys.exit(0)
    else:
        print("Iceberg setup failed!")
        sys.exit(1)
