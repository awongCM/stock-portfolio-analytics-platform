"""Calculate and store technical indicators."""

from typing import List
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, avg, stddev, lag, when
from pyspark.sql.window import Window
from ..iceberg.catalog import IcebergCatalog


class TechnicalIndicators:
    """Calculate technical indicators for stock analysis."""
    
    def __init__(self):
        self.iceberg_catalog = IcebergCatalog()
        self.spark = self.iceberg_catalog.get_spark_session()
        self.catalog_name = self.iceberg_catalog.catalog_name
    
    def calculate_sma(self, df: DataFrame, column: str = "close", periods: List[int] = [20, 50, 200]) -> DataFrame:
        """Calculate Simple Moving Average."""
        window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
        
        for period in periods:
            window = window_spec.rowsBetween(-period + 1, 0)
            df = df.withColumn(f"sma_{period}", avg(col(column)).over(window))
        
        return df
    
    def calculate_ema(self, df: DataFrame, column: str = "close", periods: List[int] = [12, 26]) -> DataFrame:
        """Calculate Exponential Moving Average."""
        for period in periods:
            alpha = 2 / (period + 1)
            
            # This is a simplified EMA calculation
            # In production, you'd want a more accurate recursive calculation
            window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
            window = window_spec.rowsBetween(-period + 1, 0)
            
            df = df.withColumn(f"ema_{period}", avg(col(column)).over(window))
        
        return df
    
    def calculate_rsi(self, df: DataFrame, period: int = 14) -> DataFrame:
        """Calculate Relative Strength Index."""
        window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
        
        # Calculate price changes
        df = df.withColumn("price_change", col("close") - lag("close").over(window_spec))
        
        # Separate gains and losses
        df = df.withColumn("gain", when(col("price_change") > 0, col("price_change")).otherwise(0))
        df = df.withColumn("loss", when(col("price_change") < 0, -col("price_change")).otherwise(0))
        
        # Calculate average gains and losses
        window = window_spec.rowsBetween(-period + 1, 0)
        df = df.withColumn("avg_gain", avg("gain").over(window))
        df = df.withColumn("avg_loss", avg("loss").over(window))
        
        # Calculate RS and RSI
        df = df.withColumn("rs", col("avg_gain") / col("avg_loss"))
        df = df.withColumn("rsi_14", 100 - (100 / (1 + col("rs"))))
        
        return df.drop("price_change", "gain", "loss", "avg_gain", "avg_loss", "rs")
    
    def calculate_bollinger_bands(self, df: DataFrame, period: int = 20, std_dev: int = 2) -> DataFrame:
        """Calculate Bollinger Bands."""
        window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
        window = window_spec.rowsBetween(-period + 1, 0)
        
        # Calculate middle band (SMA)
        df = df.withColumn("bb_middle", avg("close").over(window))
        
        # Calculate standard deviation
        df = df.withColumn("bb_std", stddev("close").over(window))
        
        # Calculate upper and lower bands
        df = df.withColumn("bollinger_upper", col("bb_middle") + (col("bb_std") * std_dev))
        df = df.withColumn("bollinger_lower", col("bb_middle") - (col("bb_std") * std_dev))
        
        return df.drop("bb_middle", "bb_std")
    
    def calculate_macd(self, df: DataFrame) -> DataFrame:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        # Calculate EMA 12 and 26
        df = self.calculate_ema(df, periods=[12, 26])
        
        # MACD line = EMA12 - EMA26
        df = df.withColumn("macd", col("ema_12") - col("ema_26"))
        
        # Signal line = 9-period EMA of MACD
        window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
        window = window_spec.rowsBetween(-8, 0)
        df = df.withColumn("macd_signal", avg("macd").over(window))
        
        return df
    
    def calculate_all_indicators(self, stock_symbol: str) -> DataFrame:
        """Calculate all technical indicators for a stock."""
        # Load stock prices
        df = self.spark.sql(f"""
            SELECT *
            FROM {self.catalog_name}.portfolio.stock_prices
            WHERE stock_symbol = '{stock_symbol}'
            ORDER BY timestamp
        """)
        
        # Calculate all indicators
        df = self.calculate_sma(df)
        df = self.calculate_ema(df)
        df = self.calculate_rsi(df)
        df = self.calculate_bollinger_bands(df)
        df = self.calculate_macd(df)
        
        # Select only necessary columns
        result = df.select(
            "stock_symbol",
            "timestamp",
            "sma_20", "sma_50", "sma_200",
            "ema_12", "ema_26",
            "rsi_14",
            "macd", "macd_signal",
            "bollinger_upper", "bollinger_lower"
        )
        
        return result
    
    def store_indicators(self, stock_symbol: str) -> None:
        """Calculate and store technical indicators in Iceberg."""
        indicators = self.calculate_all_indicators(stock_symbol)
        
        # Write to Iceberg
        indicators.writeTo(f"{self.catalog_name}.portfolio.technical_indicators") \
            .using("iceberg") \
            .append()
        
        print(f"Stored technical indicators for {stock_symbol}")
