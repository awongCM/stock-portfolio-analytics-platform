"""Table management utilities for Apache Iceberg."""

from typing import Optional
from pyiceberg.catalog import Catalog
from pyiceberg.schema import Schema
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform, IdentityTransform
from .catalog import IcebergCatalog
from .schemas import (
    STOCK_PRICES_SCHEMA,
    TRANSACTIONS_SCHEMA,
    PORTFOLIO_METRICS_SCHEMA,
    TECHNICAL_INDICATORS_SCHEMA,
    SECURITIES_SCHEMA,
    EXCHANGE_RATES_SCHEMA,
)


class IcebergTableManager:
    """Manages Iceberg table creation and operations."""
    
    def __init__(self, catalog: Optional[Catalog] = None):
        if catalog is None:
            iceberg_catalog = IcebergCatalog()
            self.catalog = iceberg_catalog.initialize_catalog()
        else:
            self.catalog = catalog
    
    def create_stock_prices_table(self, namespace: str = "portfolio") -> None:
        """Create stock prices table partitioned by date."""
        table_name = f"{namespace}.stock_prices"
        
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=2,  # timestamp field
                field_id=1000,
                transform=DayTransform(),
                name="day"
            ),
            PartitionField(
                source_id=1,  # stock_symbol field
                field_id=1001,
                transform=IdentityTransform(),
                name="stock_symbol"
            )
        )
        
        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=STOCK_PRICES_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")
    
    def create_transactions_table(self, namespace: str = "portfolio") -> None:
        """Create transactions table partitioned by date."""
        table_name = f"{namespace}.transactions"
        
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=8,  # transaction_date field
                field_id=1000,
                transform=DayTransform(),
                name="day"
            ),
            PartitionField(
                source_id=2,  # portfolio_id field
                field_id=1001,
                transform=IdentityTransform(),
                name="portfolio_id"
            )
        )
        
        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=TRANSACTIONS_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")
    
    def create_portfolio_metrics_table(self, namespace: str = "portfolio") -> None:
        """Create portfolio metrics table."""
        table_name = f"{namespace}.portfolio_metrics"
        
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=2,  # calculation_date field
                field_id=1000,
                transform=DayTransform(),
                name="day"
            ),
            PartitionField(
                source_id=1,  # portfolio_id field
                field_id=1001,
                transform=IdentityTransform(),
                name="portfolio_id"
            )
        )
        
        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=PORTFOLIO_METRICS_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")
    
    def create_technical_indicators_table(self, namespace: str = "portfolio") -> None:
        """Create technical indicators table."""
        table_name = f"{namespace}.technical_indicators"
        
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=2,  # timestamp field
                field_id=1000,
                transform=DayTransform(),
                name="day"
            ),
            PartitionField(
                source_id=1,  # stock_symbol field
                field_id=1001,
                transform=IdentityTransform(),
                name="stock_symbol"
            )
        )
        
        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=TECHNICAL_INDICATORS_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")

    def create_securities_table(self, namespace: str = "portfolio") -> None:
        """Create securities dimension table partitioned by market."""
        table_name = f"{namespace}.securities"

        partition_spec = PartitionSpec(
            PartitionField(
                source_id=8,  # market_code field
                field_id=1000,
                transform=IdentityTransform(),
                name="market_code",
            )
        )

        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=SECURITIES_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")

    def create_exchange_rates_table(self, namespace: str = "portfolio") -> None:
        """Create exchange rates table partitioned by day."""
        table_name = f"{namespace}.exchange_rates"

        partition_spec = PartitionSpec(
            PartitionField(
                source_id=3,  # timestamp field
                field_id=1000,
                transform=DayTransform(),
                name="day",
            )
        )

        try:
            self.catalog.create_table(
                identifier=table_name,
                schema=EXCHANGE_RATES_SCHEMA,
                partition_spec=partition_spec,
            )
            print(f"Created table: {table_name}")
        except Exception as e:
            print(f"Error creating {table_name}: {e}")

    def create_all_tables(self, namespace: str = "portfolio") -> None:
        """Create all Iceberg tables."""
        # Ensure namespace exists
        iceberg_catalog = IcebergCatalog()
        iceberg_catalog.create_namespace(namespace)
        
        # Create tables
        self.create_stock_prices_table(namespace)
        self.create_transactions_table(namespace)
        self.create_portfolio_metrics_table(namespace)
        self.create_technical_indicators_table(namespace)
        self.create_securities_table(namespace)
        self.create_exchange_rates_table(namespace)
        
        print(f"All tables created in namespace: {namespace}")
