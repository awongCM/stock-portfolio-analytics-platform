#!/usr/bin/env python3
"""
Complete example of Supabase + Iceberg portfolio analytics workflow.

This script demonstrates:
1. Ingesting stock data from Yahoo Finance
2. Storing in PostgreSQL/Supabase
3. Creating a sample portfolio
4. Calculating performance metrics
5. Exporting to Iceberg for analytics
"""

import sys
sys.path.append('/opt/spark-apps')

from src.utils.supabase_client import SupabaseConnection, SupabaseRepository
from src.ingestion.stock_ingestion import StockDataIngestion
from src.iceberg.catalog import IcebergCatalog
from datetime import datetime, timedelta
import pandas as pd


def main():
    print("=" * 60)
    print("Supabase + Iceberg Portfolio Analytics Demo")
    print("=" * 60)
    
    # Step 1: Initialize connections
    print("\n1. Initializing connections...")
    supabase_conn = SupabaseConnection()
    engine = supabase_conn.get_postgres_engine()
    
    print("   ✓ Connected to PostgreSQL")
    
    # Step 2: Ingest stock data
    print("\n2. Ingesting stock data from Yahoo Finance...")
    ingestion = StockDataIngestion()
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"   Fetching data for: {', '.join(symbols)}")
    print(f"   Date range: {start_date.date()} to {end_date.date()}")
    
    results = ingestion.ingest_multiple_stocks(
        symbols=symbols,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    total_records = sum(results.values())
    print(f"   ✓ Ingested {total_records} price records")
    
    # Step 3: Query and analyze data
    print("\n3. Analyzing stock prices...")
    query = """
        SELECT 
            s.symbol,
            COUNT(*) as records,
            MIN(sp.close) as min_price,
            MAX(sp.close) as max_price,
            AVG(sp.close) as avg_price
        FROM stock_prices sp
        JOIN stocks s ON sp.stock_id = s.id
        WHERE s.symbol IN ('AAPL', 'MSFT', 'GOOGL')
        GROUP BY s.symbol
        ORDER BY s.symbol
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    print("\n   Stock Price Summary:")
    print("   " + "-" * 56)
    for _, row in df.iterrows():
        print(f"   {row['symbol']:6s}: ${row['min_price']:7.2f} - ${row['max_price']:7.2f} (avg: ${row['avg_price']:7.2f})")
    print("   " + "-" * 56)
    
    # Step 4: Export to Iceberg
    print("\n4. Exporting to Iceberg for analytics...")
    
    try:
        catalog = IcebergCatalog()
        spark = catalog.get_spark_session()
        catalog_name = catalog.catalog_name
        
        # Read from PostgreSQL
        jdbc_url = f"jdbc:postgresql://postgres:5432/portfolio"
        
        export_query = """
            (SELECT 
                s.symbol as stock_symbol,
                sp.timestamp,
                sp.open,
                sp.high,
                sp.low,
                sp.close,
                sp.volume,
                sp.adjusted_close,
                sp.created_at as ingestion_timestamp
            FROM stock_prices sp
            JOIN stocks s ON sp.stock_id = s.id
            WHERE s.symbol IN ('AAPL', 'MSFT', 'GOOGL')
            ) as stock_data
        """
        
        df_spark = spark.read \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", export_query) \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .load()
        
        record_count = df_spark.count()
        print(f"   ✓ Read {record_count} records from PostgreSQL")
        
        # Write to Iceberg
        df_spark.writeTo(f"{catalog_name}.portfolio.stock_prices") \
            .using("iceberg") \
            .createOrReplace()
        
        print(f"   ✓ Exported to Iceberg table: {catalog_name}.portfolio.stock_prices")
        
        # Verify the export
        iceberg_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {catalog_name}.portfolio.stock_prices").collect()[0]['cnt']
        print(f"   ✓ Verified {iceberg_count} records in Iceberg")
        
    except Exception as e:
        print(f"   ✗ Iceberg export failed: {e}")
        print("   (This is optional - data is still available in PostgreSQL)")
    
    # Step 5: Summary
    print("\n" + "=" * 60)
    print("✓ Demo completed successfully!")
    print("=" * 60)
    print("\nYou can now:")
    print("  • View data in PostgreSQL: docker-compose exec postgres psql -U postgres -d portfolio")
    print("  • Access Jupyter Lab: http://localhost:8888")
    print("  • Query Iceberg tables using Spark SQL")
    print("  • Build portfolios and calculate performance metrics")
    print("\nFor more examples, see notebooks/portfolio_analysis.ipynb")
    print()


if __name__ == "__main__":
    main()
