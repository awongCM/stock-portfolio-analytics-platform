#!/usr/bin/env python3
"""Insert sample stock price data directly into PostgreSQL."""

import sys
sys.path.append('/opt/spark-apps')

from datetime import datetime, timedelta
from decimal import Decimal
import random
from sqlalchemy import text
from src.utils.supabase_client import get_postgres_engine


def generate_sample_prices(symbol: str, days: int = 30):
    """Generate sample stock prices."""
    base_prices = {
        'AAPL': 175.0,
        'MSFT': 370.0,
        'GOOGL': 140.0,
        'AMZN': 150.0,
        'TSLA': 240.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    prices = []
    
    current_date = datetime.now() - timedelta(days=days)
    current_price = base_price
    
    for i in range(days):
        # Simulate daily price movement
        change_pct = random.uniform(-0.03, 0.03)  # -3% to +3%
        current_price = current_price * (1 + change_pct)
        
        daily_volatility = current_price * 0.01
        open_price = current_price + random.uniform(-daily_volatility, daily_volatility)
        high_price = max(open_price, current_price) + random.uniform(0, daily_volatility)
        low_price = min(open_price, current_price) - random.uniform(0, daily_volatility)
        close_price = current_price
        volume = random.randint(50_000_000, 150_000_000)
        
        prices.append({
            'timestamp': current_date + timedelta(days=i),
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume,
            'adjusted_close': round(close_price, 2)
        })
    
    return prices


def main():
    print("=" * 60)
    print("Inserting Sample Stock Price Data")
    print("=" * 60)
    
    engine = get_postgres_engine()
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    total_inserted = 0
    
    for symbol in symbols:
        print(f"\nProcessing {symbol}...")
        
        # Get stock ID
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM stocks WHERE symbol = :symbol"),
                {"symbol": symbol}
            ).fetchone()
            
            if not result:
                print(f"  ✗ Stock {symbol} not found in database")
                continue
            
            stock_id = result[0]
            
            # Generate sample prices
            prices = generate_sample_prices(symbol, days=30)
            
            # Insert prices
            inserted = 0
            for price_data in prices:
                try:
                    conn.execute(
                        text("""
                            INSERT INTO stock_prices 
                            (stock_id, timestamp, open, high, low, close, volume, adjusted_close)
                            VALUES 
                            (:stock_id, :timestamp, :open, :high, :low, :close, :volume, :adjusted_close)
                            ON CONFLICT (stock_id, timestamp) DO NOTHING
                        """),
                        {
                            "stock_id": stock_id,
                            "timestamp": price_data['timestamp'],
                            "open": price_data['open'],
                            "high": price_data['high'],
                            "low": price_data['low'],
                            "close": price_data['close'],
                            "volume": price_data['volume'],
                            "adjusted_close": price_data['adjusted_close']
                        }
                    )
                    inserted += 1
                except Exception as e:
                    print(f"  ✗ Error inserting record: {e}")
            
            conn.commit()
            total_inserted += inserted
            print(f"  ✓ Inserted {inserted} price records")
    
    print("\n" + "=" * 60)
    print(f"✓ Total: {total_inserted} price records inserted")
    print("=" * 60)
    
    # Show summary
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                s.symbol,
                COUNT(sp.id) as price_count,
                MIN(sp.timestamp) as first_date,
                MAX(sp.timestamp) as last_date
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.id = sp.stock_id
            GROUP BY s.symbol
            ORDER BY s.symbol
        """))
        
        print("\nDatabase Summary:")
        print("-" * 60)
        for row in result:
            print(f"  {row[0]:6s}: {row[1]:4d} prices  ({row[2]} to {row[3]})")
        print("-" * 60)


if __name__ == "__main__":
    main()
