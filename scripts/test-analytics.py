#!/usr/bin/env python3
"""Test portfolio analytics using PostgreSQL directly."""

import sys
sys.path.append('/opt/spark-apps')

from datetime import datetime, timedelta
from sqlalchemy import text
from src.utils.supabase_client import get_postgres_engine
import pandas as pd


def test_portfolio_analysis():
    """Test portfolio performance calculations."""
    print("=" * 70)
    print("Testing Portfolio Performance Analysis (PostgreSQL)")
    print("=" * 70)
    
    engine = get_postgres_engine()
    
    with engine.connect() as conn:
        # Get portfolio ID - get the one with transactions
        result = conn.execute(text("""
            SELECT p.id, p.name, COUNT(t.id) as transaction_count
            FROM portfolios p
            LEFT JOIN transactions t ON p.id = t.portfolio_id
            GROUP BY p.id, p.name
            ORDER BY COUNT(t.id) DESC
            LIMIT 1
        """))
        row = result.fetchone()
        portfolio_id = row[0]
        portfolio_name = row[1]
        
        print(f"\nPortfolio: {portfolio_name}")
        print(f"ID: {portfolio_id}")
        
        # Calculate current holdings and performance
        print("\n1. Current Holdings & Performance:")
        print("-" * 70)
        
        result = conn.execute(text("""
            WITH holdings AS (
                SELECT 
                    s.id as stock_id,
                    s.symbol,
                    SUM(CASE 
                        WHEN t.transaction_type = 'BUY' THEN t.quantity
                        WHEN t.transaction_type = 'SELL' THEN -t.quantity
                    END) as total_quantity,
                    SUM(CASE 
                        WHEN t.transaction_type = 'BUY' THEN t.quantity * t.price
                        WHEN t.transaction_type = 'SELL' THEN -t.quantity * t.price
                    END) as total_cost
                FROM transactions t
                JOIN stocks s ON t.stock_id = s.id
                WHERE t.portfolio_id = :portfolio_id
                GROUP BY s.id, s.symbol
            ),
            latest_prices AS (
                SELECT DISTINCT ON (stock_id)
                    stock_id,
                    close as current_price,
                    timestamp
                FROM stock_prices
                ORDER BY stock_id, timestamp DESC
            )
            SELECT 
                h.symbol,
                h.total_quantity as quantity,
                ROUND(h.total_cost / h.total_quantity, 2) as avg_cost,
                ROUND(lp.current_price, 2) as current_price,
                ROUND(h.total_quantity * lp.current_price, 2) as market_value,
                ROUND((lp.current_price - (h.total_cost / h.total_quantity)) * h.total_quantity, 2) as unrealized_pnl,
                ROUND((lp.current_price / (h.total_cost / h.total_quantity) - 1) * 100, 2) as pnl_pct
            FROM holdings h
            JOIN latest_prices lp ON lp.stock_id = h.stock_id
            WHERE h.total_quantity > 0
            ORDER BY h.symbol
        """), {"portfolio_id": portfolio_id})
        
        holdings = result.fetchall()
        
        total_cost = 0
        total_value = 0
        
        print(f"{'Symbol':<8} {'Qty':>8} {'Avg Cost':>10} {'Current':>10} {'Market Val':>12} {'Unreal P/L':>12} {'%':>8}")
        print("-" * 70)
        
        for row in holdings:
            symbol, qty, avg_cost, current, value, pnl, pnl_pct = row
            total_cost += float(avg_cost) * float(qty)
            total_value += float(value)
            print(f"{symbol:<8} {qty:>8.0f} ${avg_cost:>9.2f} ${current:>9.2f} ${value:>11.2f} ${pnl:>10.2f} {pnl_pct:>7.1f}%")
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        print("-" * 70)
        print(f"{'TOTAL':<8} {'':<8} ${total_cost:>9.2f} {'':<10} ${total_value:>11.2f} ${total_pnl:>10.2f} {total_pnl_pct:>7.1f}%")
        
        print("\n✓ Portfolio analysis complete!")


def test_technical_indicators():
    """Test technical indicator calculations using PostgreSQL."""
    print("\n" + "=" * 70)
    print("Testing Technical Indicators (PostgreSQL)")
    print("=" * 70)
    
    engine = get_postgres_engine()
    
    with engine.connect() as conn:
        # Get a stock
        result = conn.execute(text("SELECT id, symbol FROM stocks WHERE symbol = 'AAPL'"))
        row = result.fetchone()
        stock_id, symbol = row
        
        # Get prices for technical analysis
        result = conn.execute(text("""
            SELECT 
                timestamp,
                close
            FROM stock_prices
            WHERE stock_id = :stock_id
            ORDER BY timestamp DESC
            LIMIT 30
        """), {"stock_id": stock_id})
        
        prices = [(row[0], float(row[1])) for row in result]
        prices.reverse()  # Oldest first
        
        if len(prices) >= 14:
            # Calculate Simple Moving Average (14-day)
            sma_period = 14
            closes = [p[1] for p in prices]
            sma = sum(closes[-sma_period:]) / sma_period
            
            # Calculate RSI (14-day)
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            if len(gains) >= sma_period:
                avg_gain = sum(gains[-sma_period:]) / sma_period
                avg_loss = sum(losses[-sma_period:]) / sma_period
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50  # Neutral
            
            # Calculate Bollinger Bands
            std_dev = (sum((x - sma) ** 2 for x in closes[-sma_period:]) / sma_period) ** 0.5
            bb_upper = sma + (2 * std_dev)
            bb_lower = sma - (2 * std_dev)
            bb_width = ((bb_upper - bb_lower) / sma) * 100
            
            latest_price = closes[-1]
            latest_date = prices[-1][0]
            
            print(f"\n1. Technical Indicators for {symbol}:")
            print("-" * 70)
            print(f"   Date: {latest_date}")
            print(f"   Current Price: ${latest_price:.2f}")
            print(f"\n   Moving Averages:")
            print(f"   - SMA ({sma_period}): ${sma:.2f}")
            print(f"\n   Momentum:")
            print(f"   - RSI ({sma_period}): {rsi:.2f}")
            print(f"\n   Volatility:")
            print(f"   - BB Upper: ${bb_upper:.2f}")
            print(f"   - BB Middle: ${sma:.2f}")
            print(f"   - BB Lower: ${bb_lower:.2f}")
            print(f"   - BB Width: {bb_width:.2f}%")
            
            # Show analysis
            print(f"\n   Analysis:")
            if rsi > 70:
                print(f"   - RSI indicates OVERBOUGHT condition")
            elif rsi < 30:
                print(f"   - RSI indicates OVERSOLD condition")
            else:
                print(f"   - RSI indicates NEUTRAL condition")
            
            if latest_price > bb_upper:
                print(f"   - Price above upper Bollinger Band (overbought)")
            elif latest_price < bb_lower:
                print(f"   - Price below lower Bollinger Band (oversold)")
            else:
                print(f"   - Price within Bollinger Bands (normal)")
            
            if latest_price > sma:
                print(f"   - Price above SMA (bullish)")
            else:
                print(f"   - Price below SMA (bearish)")
        
        print("\n✓ Technical indicators calculation complete!")


def main():
    """Run all tests."""
    try:
        test_portfolio_analysis()
        test_technical_indicators()
        
        print("\n" + "=" * 70)
        print("✓ All Analytics Tests Passed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
