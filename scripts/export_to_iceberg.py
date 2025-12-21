"""Export data from Supabase to Iceberg - Spark job."""

import sys
sys.path.append('/opt/spark-apps')

from src.ingestion.iceberg_exporter import SupabaseToIcebergExporter


def main():
    """Main export job."""
    exporter = SupabaseToIcebergExporter()
    
    print("Starting data export to Iceberg...")
    
    # Export all data
    exporter.export_stock_prices_to_iceberg()
    exporter.export_transactions_to_iceberg()
    
    print("Export completed successfully!")


if __name__ == "__main__":
    main()
