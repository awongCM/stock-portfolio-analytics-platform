"""Portfolio performance analytics using PySpark and Iceberg."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, sum, avg, stddev, max, min, lag, lead,
    when, datediff, expr, window, row_number, lit, coalesce, first, count
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

    def _get_latest_prices_df(self, symbols: list, as_of_date: Optional[str] = None) -> DataFrame:
        """Latest close price per symbol as of date."""
        if not as_of_date:
            as_of_date = datetime.now().isoformat()
        quoted = ",".join([f"'{s}'" for s in symbols])
        return self.spark.sql(f"""
            SELECT stock_symbol, close AS current_price
            FROM (
                SELECT stock_symbol, close,
                    ROW_NUMBER() OVER (
                        PARTITION BY stock_symbol ORDER BY timestamp DESC
                    ) AS rn
                FROM {self.catalog_name}.portfolio.stock_prices
                WHERE stock_symbol IN ({quoted})
                  AND timestamp <= '{as_of_date}'
            )
            WHERE rn = 1
        """)

    def _get_securities_df(self) -> DataFrame:
        """Securities dimension with sector and region metadata."""
        return self.spark.sql(f"""
            SELECT
                stock_symbol,
                COALESCE(gics_sector_override, gics_sector, 'Unknown') AS gics_sector,
                gics_sector_code,
                COALESCE(country_code, 'Unknown') AS country_code,
                COALESCE(quote_currency, 'USD') AS quote_currency,
                COALESCE(market_code, 'Unknown') AS market_code
            FROM {self.catalog_name}.portfolio.securities
        """)

    def _get_latest_fx_rates_df(self, base_currency: str = "AUD") -> DataFrame:
        """Latest FX rate per currency pair for conversion to base currency."""
        return self.spark.sql(f"""
            SELECT base_currency, quote_currency, rate
            FROM (
                SELECT base_currency, quote_currency, rate,
                    ROW_NUMBER() OVER (
                        PARTITION BY base_currency, quote_currency
                        ORDER BY timestamp DESC
                    ) AS rn
                FROM {self.catalog_name}.portfolio.exchange_rates
            )
            WHERE rn = 1
        """)

    def _holdings_with_base_value(
        self,
        base_currency: str = "AUD",
        as_of_date: Optional[str] = None,
    ) -> DataFrame:
        """Holdings joined with prices, securities, and FX-converted market value."""
        holdings = self.calculate_current_holdings()
        symbols = [row.stock_symbol for row in holdings.collect()]
        if not symbols:
            return self.spark.createDataFrame(
                [],
                "stock_symbol STRING, total_quantity DOUBLE, total_cost DOUBLE, "
                "average_cost DOUBLE, current_price DOUBLE, gics_sector STRING, "
                "country_code STRING, quote_currency STRING, market_code STRING, "
                "local_market_value DOUBLE, fx_multiplier DOUBLE, market_value_base DOUBLE",
            )

        prices = self._get_latest_prices_df(symbols, as_of_date)
        securities = self._get_securities_df()
        fx = self._get_latest_fx_rates_df(base_currency)

        enriched = (
            holdings
            .join(prices, on="stock_symbol", how="inner")
            .join(securities, on="stock_symbol", how="left")
            .withColumn(
                "local_market_value",
                col("total_quantity") * col("current_price"),
            )
        )

        # Direct rate: 1 base = rate quote → value_base = local_value / rate
        direct_fx = fx.filter(col("base_currency") == lit(base_currency)).select(
            col("quote_currency").alias("fx_quote"),
            col("rate").alias("direct_rate"),
        )

        # Inverse rate: 1 quote = rate base → value_base = local_value * rate
        inverse_fx = fx.filter(col("quote_currency") == lit(base_currency)).select(
            col("base_currency").alias("inv_base"),
            col("rate").alias("inverse_rate"),
        )

        enriched = enriched.join(
            direct_fx,
            enriched.quote_currency == direct_fx.fx_quote,
            how="left",
        ).join(
            inverse_fx,
            enriched.quote_currency == inverse_fx.inv_base,
            how="left",
        )

        enriched = enriched.withColumn(
            "fx_multiplier",
            when(col("quote_currency") == lit(base_currency), lit(1.0))
            .when(col("direct_rate").isNotNull(), lit(1.0) / col("direct_rate"))
            .when(col("inverse_rate").isNotNull(), col("inverse_rate"))
            .otherwise(lit(1.0)),
        ).withColumn(
            "market_value_base",
            col("local_market_value") * col("fx_multiplier"),
        )

        return enriched

    def get_sector_allocation(
        self,
        base_currency: str = "AUD",
        as_of_date: Optional[str] = None,
    ) -> DataFrame:
        """
        Sector weights by GICS sector with multi-currency conversion.

        Returns DataFrame: gics_sector, market_value_base, weight_pct, num_holdings
        """
        enriched = self._holdings_with_base_value(base_currency, as_of_date)
        if not enriched.head(1):
            return self.spark.createDataFrame(
                [],
                "gics_sector STRING, market_value_base DOUBLE, weight_pct DOUBLE, "
                "total_quantity DOUBLE, avg_fx_rate DOUBLE",
            )

        sector_agg = enriched.groupBy("gics_sector").agg(
            sum("market_value_base").alias("market_value_base"),
            sum("total_quantity").alias("total_quantity"),
            avg("fx_multiplier").alias("avg_fx_rate"),
            count("stock_symbol").alias("num_holdings"),
        )

        total = sector_agg.agg(sum("market_value_base").alias("total")).collect()[0]["total"] or 0

        return sector_agg.withColumn(
            "weight_pct",
            when(lit(total) > 0, (col("market_value_base") / lit(total)) * 100).otherwise(lit(0.0)),
        ).select(
            "gics_sector",
            "market_value_base",
            "weight_pct",
            "total_quantity",
            "avg_fx_rate",
        ).orderBy(col("weight_pct").desc())

    def get_region_allocation(
        self,
        base_currency: str = "AUD",
        as_of_date: Optional[str] = None,
    ) -> DataFrame:
        """
        Regional weights by country_code with multi-currency conversion.

        Returns DataFrame: country_code, market_code, market_value_base, weight_pct
        """
        enriched = self._holdings_with_base_value(base_currency, as_of_date)
        if not enriched.head(1):
            return self.spark.createDataFrame(
                [],
                "country_code STRING, market_code STRING, market_value_base DOUBLE, weight_pct DOUBLE",
            )

        region_agg = enriched.groupBy("country_code", "market_code").agg(
            sum("market_value_base").alias("market_value_base"),
        )

        total = region_agg.agg(sum("market_value_base").alias("total")).collect()[0]["total"] or 0

        return region_agg.withColumn(
            "weight_pct",
            when(lit(total) > 0, (col("market_value_base") / lit(total)) * 100).otherwise(lit(0.0)),
        ).orderBy(col("weight_pct").desc())
