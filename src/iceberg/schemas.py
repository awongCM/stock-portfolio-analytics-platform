"""Table schema definitions for Iceberg tables."""

from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField,
    StringType,
    DoubleType,
    LongType,
    TimestampType,
    DecimalType,
)


# Stock prices historical data schema
STOCK_PRICES_SCHEMA = Schema(
    NestedField(1, "stock_symbol", StringType(), required=True),
    NestedField(2, "timestamp", TimestampType(), required=True),
    NestedField(3, "open", DecimalType(20, 6), required=True),
    NestedField(4, "high", DecimalType(20, 6), required=True),
    NestedField(5, "low", DecimalType(20, 6), required=True),
    NestedField(6, "close", DecimalType(20, 6), required=True),
    NestedField(7, "volume", LongType(), required=True),
    NestedField(8, "adjusted_close", DecimalType(20, 6), required=False),
    NestedField(9, "ingestion_timestamp", TimestampType(), required=True),
)

# Portfolio transactions historical data
TRANSACTIONS_SCHEMA = Schema(
    NestedField(1, "transaction_id", StringType(), required=True),
    NestedField(2, "portfolio_id", StringType(), required=True),
    NestedField(3, "stock_symbol", StringType(), required=True),
    NestedField(4, "transaction_type", StringType(), required=True),
    NestedField(5, "quantity", DecimalType(20, 6), required=True),
    NestedField(6, "price", DecimalType(20, 6), required=True),
    NestedField(7, "commission", DecimalType(20, 6), required=True),
    NestedField(8, "transaction_date", TimestampType(), required=True),
    NestedField(9, "ingestion_timestamp", TimestampType(), required=True),
)

# Portfolio performance metrics
PORTFOLIO_METRICS_SCHEMA = Schema(
    NestedField(1, "portfolio_id", StringType(), required=True),
    NestedField(2, "calculation_date", TimestampType(), required=True),
    NestedField(3, "total_value", DecimalType(20, 2), required=True),
    NestedField(4, "total_cost", DecimalType(20, 2), required=True),
    NestedField(5, "realized_gains", DecimalType(20, 2), required=True),
    NestedField(6, "unrealized_gains", DecimalType(20, 2), required=True),
    NestedField(7, "total_return_pct", DoubleType(), required=True),
    NestedField(8, "daily_return_pct", DoubleType(), required=False),
    NestedField(9, "volatility", DoubleType(), required=False),
    NestedField(10, "sharpe_ratio", DoubleType(), required=False),
    NestedField(11, "max_drawdown_pct", DoubleType(), required=False),
)

# Stock technical indicators
TECHNICAL_INDICATORS_SCHEMA = Schema(
    NestedField(1, "stock_symbol", StringType(), required=True),
    NestedField(2, "timestamp", TimestampType(), required=True),
    NestedField(3, "sma_20", DecimalType(20, 6), required=False),
    NestedField(4, "sma_50", DecimalType(20, 6), required=False),
    NestedField(5, "sma_200", DecimalType(20, 6), required=False),
    NestedField(6, "ema_12", DecimalType(20, 6), required=False),
    NestedField(7, "ema_26", DecimalType(20, 6), required=False),
    NestedField(8, "rsi_14", DoubleType(), required=False),
    NestedField(9, "macd", DecimalType(20, 6), required=False),
    NestedField(10, "macd_signal", DecimalType(20, 6), required=False),
    NestedField(11, "bollinger_upper", DecimalType(20, 6), required=False),
    NestedField(12, "bollinger_lower", DecimalType(20, 6), required=False),
)
