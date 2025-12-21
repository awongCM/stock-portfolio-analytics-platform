"""Stock data ingestion from external APIs to Supabase."""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import yfinance as yf
import pandas as pd
from sqlalchemy import text
from ..utils.supabase_client import get_postgres_engine


class StockDataIngestion:
    """Handles stock data ingestion from Yahoo Finance."""
    
    def __init__(self):
        self.engine = get_postgres_engine()
    
    def ensure_stock_exists(self, symbol: str) -> str:
        """Ensure stock record exists in database, create if not."""
        # Check if stock exists
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM stocks WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).fetchone()
            
            if result:
                return result[0]
        
        # Fetch stock info from yfinance
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        stock_data = {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "exchange": info.get("exchange", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
        }
        
        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO stocks (symbol, name, exchange, sector, industry)
                    VALUES (:symbol, :name, :exchange, :sector, :industry)
                    RETURNING id
                """),
                stock_data
            )
            conn.commit()
            return result.fetchone()[0]
    
    def fetch_stock_prices(
        self, 
        symbol: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo"
    ) -> pd.DataFrame:
        """Fetch stock prices from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        
        if start_date and end_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)
        
        return df
    
    def ingest_stock_prices(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo"
    ) -> int:
        """Ingest stock prices into Supabase."""
        # Ensure stock exists
        stock_id = self.ensure_stock_exists(symbol)
        
        # Fetch price data
        df = self.fetch_stock_prices(symbol, start_date, end_date, period)
        
        if df.empty:
            print(f"No data fetched for {symbol}")
            return 0
        
        # Prepare data for insertion
        records = []
        for timestamp, row in df.iterrows():
            record = {
                "stock_id": stock_id,
                "timestamp": timestamp.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
                "adjusted_close": float(row["Close"]),  # yfinance already provides adjusted close
            }
            records.append(record)
        
        # Insert in batches
        batch_size = 1000
        inserted_count = 0
        
        with self.engine.connect() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                try:
                    for record in batch:
                        conn.execute(
                            text("""
                                INSERT INTO stock_prices 
                                (stock_id, timestamp, open, high, low, close, volume, adjusted_close)
                                VALUES (:stock_id, :timestamp, :open, :high, :low, :close, :volume, :adjusted_close)
                                ON CONFLICT (stock_id, timestamp) DO UPDATE SET
                                    open = EXCLUDED.open,
                                    high = EXCLUDED.high,
                                    low = EXCLUDED.low,
                                    close = EXCLUDED.close,
                                    volume = EXCLUDED.volume,
                                    adjusted_close = EXCLUDED.adjusted_close
                            """),
                            record
                        )
                    conn.commit()
                    inserted_count += len(batch)
                except Exception as e:
                    print(f"Error inserting batch: {e}")
                    conn.rollback()
        
        print(f"Ingested {inserted_count} price records for {symbol}")
        return inserted_count
    
    def ingest_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo"
    ) -> Dict[str, int]:
        """Ingest price data for multiple stocks."""
        results = {}
        
        for symbol in symbols:
            try:
                count = self.ingest_stock_prices(symbol, start_date, end_date, period)
                results[symbol] = count
            except Exception as e:
                print(f"Error ingesting {symbol}: {e}")
                results[symbol] = 0
        
        return results
