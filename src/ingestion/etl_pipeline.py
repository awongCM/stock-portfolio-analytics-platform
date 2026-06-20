"""
ETL Pipeline for Portfolio Data
Orchestrates data ingestion from Yahoo Finance and populates all tables.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ETLConfig:
    """Configuration for ETL pipeline."""
    symbols: List[str]
    start_date: str
    end_date: str
    portfolio_name: str
    portfolio_description: str
    initial_cash: float = 100000.0  # Default $100k portfolio
    watchlist_path: Optional[str] = None
    regions: Optional[List[str]] = None
    base_currency: str = "AUD"
    ingest_fx: bool = True
    request_delay: float = 2.0
    batch_size: int = 10


class PortfolioETLPipeline:
    """
    Complete ETL pipeline for portfolio data.
    
    Flow:
    1. Extract: Fetch stock data from Yahoo Finance
    2. Transform: Clean and prepare data
    3. Load: Insert into PostgreSQL tables
    4. Populate: Create sample portfolio with transactions
    """
    
    def __init__(self, config: ETLConfig):
        """Initialize ETL pipeline with configuration."""
        self.config = config
        
        # Import here to avoid circular dependencies
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.ingestion.stock_ingestion import StockDataIngestion
        from src.utils.supabase_client import get_postgres_engine
        from sqlalchemy import text
        
        self.ingestion = StockDataIngestion()
        self.engine = get_postgres_engine()
        self.text = text
        self._symbol_metadata: Dict[str, Dict] = {}

        if config.watchlist_path:
            symbols, self._symbol_metadata, _, base_ccy = self.ingestion.load_watchlist(
                config.watchlist_path, config.regions
            )
            config.symbols = symbols
            if config.base_currency == "AUD" and base_ccy:
                config.base_currency = base_ccy

        logger.info("ETL Pipeline initialized")
        logger.info(f"Symbols: {len(config.symbols)} tickers")
        logger.info(f"Date range: {config.start_date} to {config.end_date}")
        if config.watchlist_path:
            logger.info(f"Watchlist: {config.watchlist_path}")
            logger.info(f"Regions: {config.regions or 'all'}")
            logger.info(f"Base currency: {config.base_currency}")
    
    def extract_and_load_stock_prices(self) -> Dict[str, int]:
        """
        Step 1: Extract stock prices from Yahoo Finance and load to stock_prices table.
        
        Returns:
            Dict mapping symbol to number of records inserted
        """
        logger.info("=" * 60)
        logger.info("STEP 1: Extracting and Loading Stock Prices")
        logger.info("=" * 60)
        
        results = {}

        if self.config.watchlist_path:
            logger.info("Using multi-region sector watchlist ingestion...")
            results = self.ingestion.ingest_watchlist(
                watchlist_path=self.config.watchlist_path,
                regions=self.config.regions,
                start_date=self.config.start_date,
                end_date=self.config.end_date,
                ingest_fx=self.config.ingest_fx,
                request_delay=self.config.request_delay,
                batch_size=self.config.batch_size,
            )
            for symbol, count in results.items():
                if symbol == "__fx__":
                    logger.info(f"  ✓ Ingested {count} FX rate records")
                elif count > 0:
                    logger.info(f"  ✓ {symbol}: {count} price records")
        else:
            for symbol in self.config.symbols:
                try:
                    logger.info(f"\nProcessing {symbol}...")
                    count = self.ingestion.ingest_stock_prices(
                        symbol=symbol,
                        start_date=self.config.start_date,
                        end_date=self.config.end_date,
                        metadata=self._symbol_metadata.get(symbol.upper()),
                    )
                    results[symbol] = count
                    logger.info(f"  ✓ Inserted {count} price records for {symbol}")
                except Exception as e:
                    logger.error(f"  ✗ Error processing {symbol}: {e}")
                    results[symbol] = 0

        total = sum(v for k, v in results.items() if k != "__fx__")
        logger.info(f"\n✓ Total price records inserted: {total}")
        
        return results
    
    def create_portfolio(self) -> str:
        """
        Step 2: Create portfolio record.
        
        Returns:
            Portfolio UUID
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Creating Portfolio")
        logger.info("=" * 60)
        
        with self.engine.connect() as conn:
            result = conn.execute(self.text("""
                INSERT INTO portfolios (name, description, currency, created_at)
                VALUES (:name, :description, :currency, NOW())
                RETURNING id
            """), {
                "name": self.config.portfolio_name,
                "description": self.config.portfolio_description,
                "currency": self.config.base_currency,
            })
            conn.commit()
            portfolio_id = result.fetchone()[0]
        
        logger.info(f"✓ Created portfolio: {self.config.portfolio_name}")
        logger.info(f"  Portfolio ID: {portfolio_id}")
        
        return portfolio_id
    
    def generate_transactions(self, portfolio_id: str) -> int:
        """
        Step 3: Generate realistic transactions based on stock prices.
        
        Strategy:
        - Allocate initial cash across stocks
        - Create buy transactions at historical prices
        - Optionally create some sell transactions
        
        Returns:
            Number of transactions created
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Generating Transactions")
        logger.info("=" * 60)
        
        # Get stock IDs and latest prices
        stock_info = {}
        with self.engine.connect() as conn:
            for symbol in self.config.symbols:
                result = conn.execute(self.text("""
                    SELECT s.id, sp.close, sp.timestamp
                    FROM stocks s
                    JOIN stock_prices sp ON s.id = sp.stock_id
                    WHERE s.symbol = :symbol
                    ORDER BY sp.timestamp DESC
                    LIMIT 1
                """), {"symbol": symbol})
                
                row = result.fetchone()
                if row:
                    stock_info[symbol] = {
                        'id': row[0],
                        'price': float(row[1]),
                        'date': row[2]
                    }
        
        if not stock_info:
            logger.error("No stock price data found. Run stock price ingestion first.")
            return 0
        
        # Allocate cash equally across stocks
        allocation_per_stock = self.config.initial_cash / len(stock_info)
        
        transaction_count = 0
        
        with self.engine.connect() as conn:
            # Calculate buy date (7 days ago from latest price)
            latest_date = max(info['date'] for info in stock_info.values())
            buy_date = latest_date - timedelta(days=7)
            
            logger.info(f"\nCreating BUY transactions (Date: {buy_date.date()}):")
            logger.info(f"Initial cash: ${self.config.initial_cash:,.2f}")
            logger.info(f"Allocation per stock: ${allocation_per_stock:,.2f}")
            
            for symbol, info in stock_info.items():
                # Get price 7 days ago
                result = conn.execute(self.text("""
                    SELECT close FROM stock_prices
                    WHERE stock_id = :stock_id
                    AND timestamp <= :date
                    ORDER BY timestamp DESC
                    LIMIT 1
                """), {
                    "stock_id": info['id'],
                    "date": buy_date
                })
                
                price_row = result.fetchone()
                if not price_row:
                    continue
                
                buy_price = float(price_row[0])
                quantity = int(allocation_per_stock / buy_price)
                
                if quantity > 0:
                    # Create BUY transaction
                    conn.execute(self.text("""
                        INSERT INTO transactions 
                        (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
                        VALUES (:portfolio_id, :stock_id, 'BUY', :quantity, :price, :date)
                    """), {
                        "portfolio_id": portfolio_id,
                        "stock_id": info['id'],
                        "quantity": quantity,
                        "price": buy_price,
                        "date": buy_date
                    })
                    
                    cost = quantity * buy_price
                    logger.info(f"  ✓ BUY {quantity:3d} {symbol:5s} @ ${buy_price:7.2f} = ${cost:10,.2f}")
                    transaction_count += 1
            
            conn.commit()
        
        logger.info(f"\n✓ Created {transaction_count} transactions")
        
        return transaction_count
    
    def verify_holdings(self, portfolio_id: str) -> None:
        """
        Step 4: Verify portfolio holdings were auto-calculated correctly.
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Verifying Portfolio Holdings")
        logger.info("=" * 60)
        
        with self.engine.connect() as conn:
            result = conn.execute(self.text("""
                SELECT 
                    s.symbol,
                    ph.quantity,
                    ph.average_cost,
                    sp.close as current_price,
                    (ph.quantity * ph.average_cost) as total_cost,
                    (ph.quantity * sp.close) as current_value,
                    ((sp.close - ph.average_cost) / ph.average_cost * 100) as pnl_pct
                FROM portfolio_holdings ph
                JOIN stocks s ON ph.stock_id = s.id
                JOIN LATERAL (
                    SELECT close 
                    FROM stock_prices 
                    WHERE stock_id = ph.stock_id 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ) sp ON true
                WHERE ph.portfolio_id = :portfolio_id
                ORDER BY s.symbol
            """), {"portfolio_id": portfolio_id})
            
            holdings = result.fetchall()
            
            if not holdings:
                logger.warning("No holdings found. Check if transactions were created.")
                return
            
            logger.info("\nCurrent Portfolio Holdings:")
            logger.info("-" * 80)
            logger.info(f"{'Symbol':<8} {'Qty':<6} {'Avg Cost':<12} {'Current':<12} {'Total Cost':<14} {'Value':<14} {'P/L %':<10}")
            logger.info("-" * 80)
            
            total_cost = 0
            total_value = 0
            
            for row in holdings:
                symbol, qty, avg_cost, current, cost, value, pnl = row
                total_cost += float(cost)
                total_value += float(value)
                
                logger.info(
                    f"{symbol:<8} {qty:<6.0f} "
                    f"${float(avg_cost):<11,.2f} ${float(current):<11,.2f} "
                    f"${float(cost):<13,.2f} ${float(value):<13,.2f} "
                    f"{float(pnl):>9.2f}%"
                )
            
            logger.info("-" * 80)
            total_pnl = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0
            logger.info(f"{'TOTAL':<8} {'':<6} {'':<12} {'':<12} ${total_cost:<13,.2f} ${total_value:<13,.2f} {total_pnl:>9.2f}%")
            logger.info("-" * 80)
            
            logger.info(f"\n✓ Portfolio verification complete")
            logger.info(f"  Total investment: ${total_cost:,.2f}")
            logger.info(f"  Current value: ${total_value:,.2f}")
            logger.info(f"  P/L: ${(total_value - total_cost):,.2f} ({total_pnl:.2f}%)")
    
    def export_to_iceberg(self) -> None:
        """
        Step 5 (Optional): Export data to Iceberg tables for analytics.
        """
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: Exporting to Iceberg (Optional)")
        logger.info("=" * 60)
        
        try:
            from src.ingestion.iceberg_exporter import SupabaseToIcebergExporter
            
            exporter = SupabaseToIcebergExporter()
            
            # Export stock prices
            logger.info("\nExporting stock prices to Iceberg...")
            exporter.export_stock_prices_to_iceberg()
            logger.info("✓ Stock prices exported")
            
            # Export transactions
            logger.info("\nExporting transactions to Iceberg...")
            exporter.export_transactions_to_iceberg()
            logger.info("✓ Transactions exported")

            # Export securities dimension
            logger.info("\nExporting securities to Iceberg...")
            exporter.export_securities_to_iceberg()
            logger.info("✓ Securities exported")

            # Export FX rates for multi-currency analytics
            logger.info("\nExporting exchange rates to Iceberg...")
            exporter.export_exchange_rates_to_iceberg()
            logger.info("✓ Exchange rates exported")
            
        except Exception as e:
            logger.warning(f"⚠ Iceberg export skipped: {e}")
            logger.info("  (This is optional - data is already in PostgreSQL)")
    
    def run(self, skip_iceberg: bool = False) -> Dict[str, any]:
        """
        Run the complete ETL pipeline.
        
        Args:
            skip_iceberg: If True, skip Iceberg export step
            
        Returns:
            Summary of ETL execution
        """
        start_time = datetime.now()
        
        logger.info("\n" + "=" * 60)
        logger.info("PORTFOLIO ETL PIPELINE - STARTED")
        logger.info("=" * 60)
        logger.info(f"Start time: {start_time}")
        
        try:
            # Step 1: Extract and load stock prices
            price_results = self.extract_and_load_stock_prices()
            
            # Step 2: Create portfolio
            portfolio_id = self.create_portfolio()
            
            # Step 3: Generate transactions (auto-updates holdings via trigger)
            transaction_count = self.generate_transactions(portfolio_id)
            
            # Step 4: Verify holdings
            self.verify_holdings(portfolio_id)
            
            # Step 5: Export to Iceberg (optional)
            if not skip_iceberg:
                self.export_to_iceberg()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            price_total = sum(
                v for k, v in price_results.items() if k != "__fx__"
            )

            summary = {
                "status": "SUCCESS",
                "duration_seconds": duration,
                "portfolio_id": portfolio_id,
                "portfolio_name": self.config.portfolio_name,
                "symbols": self.config.symbols,
                "price_records": price_total,
                "transactions": transaction_count,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Portfolio ID: {portfolio_id}")
            logger.info(f"Price records: {summary['price_records']}")
            logger.info(f"Transactions: {transaction_count}")
            
            return summary
            
        except Exception as e:
            logger.error(f"\n✗ PIPELINE FAILED: {e}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }


def create_default_pipeline(
    symbols: List[str] = None,
    days: int = 30,
    portfolio_name: str = "Automated Portfolio",
    initial_cash: float = 100000.0,
    watchlist_path: Optional[str] = None,
    regions: Optional[List[str]] = None,
    base_currency: str = "AUD",
    ingest_fx: bool = True,
    request_delay: float = 2.0,
    batch_size: int = 10,
) -> PortfolioETLPipeline:
    """
    Create a default ETL pipeline with sensible defaults.
    
    Args:
        symbols: List of stock symbols (default: AAPL, MSFT, GOOGL, AMZN, TSLA)
        days: Number of days of historical data (default: 30)
        portfolio_name: Name of the portfolio to create
        initial_cash: Initial cash to allocate (default: $100k)
    
    Returns:
        Configured ETL pipeline
    """
    if symbols is None and not watchlist_path:
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    elif watchlist_path:
        symbols = []

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    desc = (
        f"APAC sector watchlist portfolio ({regions or 'all regions'}) over {days} days"
        if watchlist_path
        else f"Auto-generated portfolio with {len(symbols)} stocks over {days} days"
    )

    config = ETLConfig(
        symbols=symbols or [],
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        portfolio_name=portfolio_name,
        portfolio_description=desc,
        initial_cash=initial_cash,
        watchlist_path=watchlist_path,
        regions=regions,
        base_currency=base_currency,
        ingest_fx=ingest_fx,
        request_delay=request_delay,
        batch_size=batch_size,
    )
    
    return PortfolioETLPipeline(config)


if __name__ == "__main__":
    """
    Run ETL pipeline from command line.
    
    Usage:
        python etl_pipeline.py
        python etl_pipeline.py --days 60
        python etl_pipeline.py --symbols AAPL MSFT GOOGL
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Portfolio ETL Pipeline')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'],
                        help='Stock symbols to ingest')
    parser.add_argument('--days', type=int, default=30,
                        help='Number of days of historical data')
    parser.add_argument('--portfolio-name', default='Automated Portfolio',
                        help='Name of the portfolio to create')
    parser.add_argument('--initial-cash', type=float, default=100000.0,
                        help='Initial cash allocation')
    parser.add_argument('--skip-iceberg', action='store_true',
                        help='Skip Iceberg export step')
    parser.add_argument('--watchlist', default=None,
                        help='Path to sector watchlist YAML (e.g. config/sector_watchlist.yaml)')
    parser.add_argument('--regions', nargs='+', default=None,
                        help='Filter watchlist regions (AU NZ MY SG)')
    parser.add_argument('--base-currency', default='AUD',
                        help='Base reporting currency (default: AUD)')
    parser.add_argument('--no-fx', action='store_true',
                        help='Skip FX rate ingestion')
    parser.add_argument('--request-delay', type=float, default=2.0,
                        help='Seconds between Yahoo Finance batch requests (default: 2.0)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Symbols per Yahoo Finance batch download (default: 10)')
    
    args = parser.parse_args()
    
    # Create and run pipeline
    pipeline = create_default_pipeline(
        symbols=args.symbols if not args.watchlist else None,
        days=args.days,
        portfolio_name=args.portfolio_name,
        initial_cash=args.initial_cash,
        watchlist_path=args.watchlist,
        regions=args.regions,
        base_currency=args.base_currency,
        ingest_fx=not args.no_fx,
        request_delay=args.request_delay,
        batch_size=args.batch_size,
    )
    
    result = pipeline.run(skip_iceberg=args.skip_iceberg)
    
    # Exit with appropriate code
    exit(0 if result['status'] == 'SUCCESS' else 1)
