"""Portfolio performance analytics using PySpark and Iceberg."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, sum, avg, stddev, max, min, lag, lead,
    when, datediff, expr, window, row_number
)
from pyspark.sql.window import Window
from decimal import Decimal
from ..iceberg.catalog import IcebergCatalog


class PortfolioAnalyzer:
    """Analyzes portfolio performance using Iceberg data."""
    
    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        self.iceberg_catalog = IcebergCatalog()
        self.spark = self.iceberg_catalog.get_spark_session()
        self.catalog_name = self.iceberg_catalog.catalog_name
    
    def get_portfolio_transactions(self) -> DataFrame:
        """Get all transactions for the portfolio."""
        return self.spark.sql(f"""
            SELECT *
            FROM {self.catalog_name}.portfolio.transactions
            WHERE portfolio_id = '{self.portfolio_id}'
            ORDER BY transaction_date
        """)
    
    def get_stock_prices(
        self,
        symbols: list,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> DataFrame:
        """Get stock prices for given symbols and date range."""
        quoted_symbols = ','.join([f"'{s}'" for s in symbols])
        where_clause = f"stock_symbol IN ({quoted_symbols})"
        
        if start_date:
            where_clause += f" AND timestamp >= '{start_date}'"
        if end_date:
            where_clause += f" AND timestamp <= '{end_date}'"
        
        return self.spark.sql(f"""
            SELECT *
            FROM {self.catalog_name}.portfolio.stock_prices
            WHERE {where_clause}
            ORDER BY stock_symbol, timestamp
        """)
    
    def calculate_current_holdings(self) -> DataFrame:
        """Calculate current portfolio holdings."""
        transactions = self.get_portfolio_transactions()
        
        # Calculate net position for each stock
        holdings = transactions.groupBy("stock_symbol").agg(
            sum(
                when(col("transaction_type") == "BUY", col("quantity"))
                .otherwise(-col("quantity"))
            ).alias("total_quantity"),
            sum(
                when(col("transaction_type") == "BUY", col("quantity") * col("price"))
                .otherwise(-col("quantity") * col("price"))
            ).alias("total_cost")
        )
        
        # Filter out zero positions
        holdings = holdings.filter(col("total_quantity") > 0)
        
        # Calculate average cost
        holdings = holdings.withColumn(
            "average_cost",
            col("total_cost") / col("total_quantity")
        )
        
        return holdings
    
    def calculate_portfolio_value(self, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Calculate total portfolio value as of a specific date."""
        if not as_of_date:
            as_of_date = datetime.now().isoformat()
        
        # Get current holdings
        holdings = self.calculate_current_holdings()
        symbols = [row.stock_symbol for row in holdings.collect()]
        
        if not symbols:
            return {
                "total_value": 0,
                "total_cost": 0,
                "unrealized_gain": 0,
                "unrealized_gain_pct": 0
            }
        
        # Get latest prices
        latest_prices = self.spark.sql(f"""
            SELECT 
                stock_symbol,
                close as current_price
            FROM (
                SELECT 
                    stock_symbol,
                    close,
                    ROW_NUMBER() OVER (
                        PARTITION BY stock_symbol 
                        ORDER BY timestamp DESC
                    ) as rn
                FROM {self.catalog_name}.portfolio.stock_prices
                WHERE stock_symbol IN ({','.join([f"'{s}'" for s in symbols])})
                    AND timestamp <= '{as_of_date}'
            )
            WHERE rn = 1
        """)
        
        # Join holdings with prices
        portfolio_value = holdings.join(
            latest_prices,
            on="stock_symbol",
            how="inner"
        )
        
        # Calculate values
        portfolio_value = portfolio_value.withColumn(
            "market_value",
            col("total_quantity") * col("current_price")
        ).withColumn(
            "unrealized_gain",
            col("market_value") - col("total_cost")
        ).withColumn(
            "unrealized_gain_pct",
            (col("unrealized_gain") / col("total_cost")) * 100
        )
        
        # Aggregate totals
        totals = portfolio_value.agg(
            sum("market_value").alias("total_value"),
            sum("total_cost").alias("total_cost"),
            sum("unrealized_gain").alias("unrealized_gain")
        ).collect()[0]
        
        total_value = float(totals["total_value"] or 0)
        total_cost = float(totals["total_cost"] or 0)
        unrealized_gain = float(totals["unrealized_gain"] or 0)
        
        return {
            "total_value": total_value,
            "total_cost": total_cost,
            "unrealized_gain": unrealized_gain,
            "unrealized_gain_pct": (unrealized_gain / total_cost * 100) if total_cost > 0 else 0,
            "holdings": portfolio_value.collect()
        }
    
    def calculate_returns(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate portfolio returns over a period."""
        if not end_date:
            end_date = datetime.now().isoformat()
        
        # Get portfolio value at start and end
        start_value = self.calculate_portfolio_value(start_date)
        end_value = self.calculate_portfolio_value(end_date)
        
        # Calculate returns
        total_return = end_value["total_value"] - start_value["total_value"]
        total_return_pct = (total_return / start_value["total_value"] * 100) if start_value["total_value"] > 0 else 0
        
        return {
            "start_value": start_value["total_value"],
            "end_value": end_value["total_value"],
            "total_return": total_return,
            "total_return_pct": total_return_pct
        }
    
    def calculate_risk_metrics(
        self,
        start_date: str,
        end_date: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate portfolio risk metrics (volatility, Sharpe ratio, max drawdown)."""
        if not end_date:
            end_date = datetime.now().isoformat()
        
        # Get daily portfolio values
        # This is simplified - in production you'd calculate actual daily values
        holdings = self.calculate_current_holdings()
        symbols = [row.stock_symbol for row in holdings.collect()]
        
        if not symbols:
            return {
                "volatility": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0
            }
        
        # Get price data
        prices = self.get_stock_prices(symbols, start_date, end_date)
        
        # Calculate daily returns
        window_spec = Window.partitionBy("stock_symbol").orderBy("timestamp")
        
        returns = prices.withColumn(
            "prev_close",
            lag("close").over(window_spec)
        ).withColumn(
            "daily_return",
            (col("close") - col("prev_close")) / col("prev_close")
        ).filter(col("prev_close").isNotNull())
        
        # Calculate portfolio-level metrics
        stats = returns.agg(
            stddev("daily_return").alias("volatility"),
            avg("daily_return").alias("avg_return")
        ).collect()[0]
        
        volatility = float(stats["volatility"] or 0) * 100  # Annualized
        avg_return = float(stats["avg_return"] or 0) * 252  # Annualized
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (avg_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Calculate max drawdown (simplified)
        max_drawdown = 0  # Would need cumulative portfolio values
        
        return {
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "avg_annual_return": avg_return
        }
