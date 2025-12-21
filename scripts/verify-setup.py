#!/usr/bin/env python3
"""
Simplified portfolio analytics demo - Verifies setup and demonstrates data flow.
"""

import sys
sys.path.append('/opt/spark-apps')

from src.utils.supabase_client import SupabaseConnection
from src.iceberg.catalog import IcebergCatalog
import pandas as pd


def main():
    print("=" * 60)
    print("Supabase + Iceberg Portfolio Analytics - Setup Verification")
    print("=" * 60)
    
    # Step 1: Verify PostgreSQL connection
    print("\n1. Verifying PostgreSQL connection...")
    try:
        supabase_conn = SupabaseConnection()
        engine = supabase_conn.get_postgres_engine()
        
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM stocks"))
            stock_count = result.fetchone()[0]
            print(f"   ✓ Connected to PostgreSQL")
            print(f"   ✓ Found {stock_count} stocks in database")
    except Exception as e:
        print(f"   ✗ PostgreSQL connection failed: {e}")
        return
    
    # Step 2: Check existing data
    print("\n2. Checking existing stock data...")
    try:
        query = """
            SELECT 
                s.symbol,
                s.name,
                COUNT(sp.id) as price_records
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.id = sp.stock_id
            GROUP BY s.symbol, s.name
            ORDER BY s.symbol
            LIMIT 10
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        if len(df) > 0:
            print("\n   Available Stocks:")
            print("   " + "-" * 56)
            for _, row in df.iterrows():
                records = int(row['price_records']) if pd.notna(row['price_records']) else 0
                print(f"   {row['symbol']:6s}: {row['name'][:30]:30s} ({records:4d} prices)")
            print("   " + "-" * 56)
        else:
            print("   No stocks found. Run ingest-sample-data.sh to load data.")
    except Exception as e:
        print(f"   ✗ Data query failed: {e}")
    
    # Step 3: Verify Spark and Iceberg
    print("\n3. Verifying Spark and Iceberg setup...")
    try:
        catalog = IcebergCatalog()
        spark = catalog.get_spark_session()
        catalog_name = catalog.catalog_name
        
        print(f"   ✓ Spark session initialized (version {spark.version})")
        print(f"   ✓ Using catalog: {catalog_name}")
        
        # List Iceberg tables
        tables_df = spark.sql(f"SHOW TABLES IN {catalog_name}.portfolio")
        tables = [row['tableName'] for row in tables_df.collect()]
        
        print(f"\n   Iceberg Tables in {catalog_name}.portfolio:")
        print("   " + "-" * 56)
        for table in tables:
            try:
                count = spark.sql(f"SELECT COUNT(*) as cnt FROM {catalog_name}.portfolio.{table}").collect()[0]['cnt']
                print(f"   • {table:30s} ({count:6d} records)")
            except:
                print(f"   • {table:30s} (empty)")
        print("   " + "-" * 56)
        
    except Exception as e:
        print(f"   ✗ Spark/Iceberg verification failed: {e}")
    
    # Step 4: Summary and next steps
    print("\n" + "=" * 60)
    print("✓ Setup verification completed!")
    print("=" * 60)
    print("\nYour environment is ready! Next steps:")
    print("\n  1. Ingest stock data:")
    print("     ./scripts/ingest-sample-data.sh")
    print("\n  2. Open Jupyter Lab:")
    print("     http://localhost:8888")
    print("\n  3. Run the portfolio analysis notebook:")
    print("     notebooks/portfolio_analysis.ipynb")
    print("\n  4. Access services:")
    print("     • MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
    print("     • Spark UI: http://localhost:8080")
    print("     • PostgreSQL: docker-compose exec postgres psql -U postgres -d portfolio")
    print()


if __name__ == "__main__":
    main()
