"""Export data from Supabase to Iceberg tables using PySpark."""

from datetime import datetime
from typing import Optional
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit, current_timestamp
from ..iceberg.catalog import IcebergCatalog
from ..utils.supabase_client import SupabaseConnection


class SupabaseToIcebergExporter:
    """Export data from Supabase PostgreSQL to Iceberg tables."""
    
    def __init__(self):
        self.iceberg_catalog = IcebergCatalog()
        self.spark = self.iceberg_catalog.get_spark_session()
        self.supabase = SupabaseConnection()
        self.postgres_engine = self.supabase.get_postgres_engine()
    
    def _jdbc_options(self) -> tuple[str, dict[str, str]]:
        """Build JDBC URL and credentials for Spark (avoid user:pass@host parsing issues)."""
        url = self.postgres_engine.url
        host = url.host or "localhost"
        port = url.port or 5432
        database = (url.database or "portfolio").lstrip("/")
        jdbc_url = f"jdbc:postgresql://{host}:{port}/{database}"
        props = {
            "user": url.username or "postgres",
            "password": url.password or "postgres",
        }
        return jdbc_url, props

    def read_from_postgres(self, table_name: str, query: Optional[str] = None) -> DataFrame:
        """Read data from PostgreSQL using PySpark."""
        jdbc_url, props = self._jdbc_options()
        reader = (
            self.spark.read.format("jdbc")
            .option("url", jdbc_url)
            .option("user", props["user"])
            .option("password", props["password"])
            .option("driver", "org.postgresql.Driver")
        )

        if query:
            df = reader.option("query", query).load()
        else:
            df = reader.option("dbtable", table_name).load()

        return df
    
    def export_stock_prices_to_iceberg(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> None:
        """Export stock prices from Supabase to Iceberg."""
        query = """
            SELECT 
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
        """
        
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append(f"sp.timestamp >= '{start_date}'")
            if end_date:
                conditions.append(f"sp.timestamp <= '{end_date}'")
            query += " WHERE " + " AND ".join(conditions)
        
        # Read from PostgreSQL
        df = self.read_from_postgres("stock_prices", query)
        
        # Write to Iceberg
        catalog_name = self.iceberg_catalog.catalog_name
        df.writeTo(f"{catalog_name}.portfolio.stock_prices") \
            .using("iceberg") \
            .createOrReplace()
        
        print(f"Exported stock prices to Iceberg table")
    
    def export_transactions_to_iceberg(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> None:
        """Export transactions from Supabase to Iceberg."""
        query = """
            SELECT 
                t.id as transaction_id,
                t.portfolio_id::text as portfolio_id,
                s.symbol as stock_symbol,
                t.transaction_type,
                t.quantity,
                t.price,
                t.commission,
                t.transaction_date,
                t.created_at as ingestion_timestamp
            FROM transactions t
            JOIN stocks s ON t.stock_id = s.id
        """
        
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append(f"t.transaction_date >= '{start_date}'")
            if end_date:
                conditions.append(f"t.transaction_date <= '{end_date}'")
            query += " WHERE " + " AND ".join(conditions)
        
        # Read from PostgreSQL
        df = self.read_from_postgres("transactions", query)
        
        # Write to Iceberg
        catalog_name = self.iceberg_catalog.catalog_name
        df.writeTo(f"{catalog_name}.portfolio.transactions") \
            .using("iceberg") \
            .append()
        
        print(f"Exported transactions to Iceberg table")

    def export_securities_to_iceberg(self) -> None:
        """Export securities dimension from Postgres to Iceberg."""
        query = """
            SELECT
                s.symbol AS stock_symbol,
                s.name,
                s.exchange,
                s.country_code,
                s.quote_currency,
                COALESCE(gs.name, s.gics_sector_override, s.sector) AS gics_sector,
                gs.code AS gics_sector_code,
                m.code AS market_code,
                s.gics_sector_override,
                s.updated_at AS ingestion_timestamp
            FROM stocks s
            LEFT JOIN gics_sectors gs ON s.gics_sector_id = gs.id
            LEFT JOIN markets m ON s.market_id = m.id
        """
        df = self.read_from_postgres("stocks", query)
        catalog_name = self.iceberg_catalog.catalog_name
        df.writeTo(f"{catalog_name}.portfolio.securities") \
            .using("iceberg") \
            .createOrReplace()
        print("Exported securities to Iceberg table")

    def export_exchange_rates_to_iceberg(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        """Export FX rates from Postgres to Iceberg."""
        query = """
            SELECT
                base_currency,
                quote_currency,
                timestamp,
                rate,
                created_at AS ingestion_timestamp
            FROM exchange_rates
        """
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append(f"timestamp >= '{start_date}'")
            if end_date:
                conditions.append(f"timestamp <= '{end_date}'")
            query += " WHERE " + " AND ".join(conditions)

        df = self.read_from_postgres("exchange_rates", query)
        catalog_name = self.iceberg_catalog.catalog_name
        df.writeTo(f"{catalog_name}.portfolio.exchange_rates") \
            .using("iceberg") \
            .createOrReplace()
        print("Exported exchange rates to Iceberg table")

    def run_incremental_export(self) -> None:
        """Run incremental export for all tables."""
        # Get last export timestamp (you would store this in a metadata table)
        last_export = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        print("Starting incremental export to Iceberg...")
        
        # Export stock prices
        self.export_stock_prices_to_iceberg(
            start_date=last_export.isoformat()
        )
        
        # Export transactions
        self.export_transactions_to_iceberg(
            start_date=last_export.isoformat()
        )

        # Export dimension tables (full refresh for POC)
        self.export_securities_to_iceberg()
        self.export_exchange_rates_to_iceberg(
            start_date=last_export.isoformat()
        )

        print("Incremental export completed")
