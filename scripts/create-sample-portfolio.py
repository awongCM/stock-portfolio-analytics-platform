#!/usr/bin/env python3
"""Create sample portfolio and transactions."""

import sys
sys.path.append('/opt/spark-apps')

from datetime import datetime, timedelta
from sqlalchemy import text
from src.utils.supabase_client import get_postgres_engine


def main():
    print("=" * 60)
    print("Creating Sample Portfolio")
    print("=" * 60)
    
    engine = get_postgres_engine()
    
    with engine.connect() as conn:
        # Create portfolio
        result = conn.execute(text("""
            INSERT INTO portfolios (name, description, created_at)
            VALUES ('Tech Growth Portfolio', 'Sample portfolio focusing on tech stocks', NOW())
            RETURNING id
        """))
        portfolio_id = result.fetchone()[0]
        print(f"\n✓ Created portfolio (ID: {portfolio_id})")
        
        # Get stock IDs
        stocks = {}
        for symbol in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']:
            result = conn.execute(
                text("SELECT id FROM stocks WHERE symbol = :symbol"),
                {"symbol": symbol}
            )
            stocks[symbol] = result.fetchone()[0]
        
        # Create buy transactions (10 days ago)
        buy_date = datetime.now() - timedelta(days=10)
        transactions = [
            ('AAPL', 100, 170.50),
            ('MSFT', 50, 365.00),
            ('GOOGL', 75, 138.00),
            ('AMZN', 60, 148.00),
            ('TSLA', 40, 235.00),
        ]
        
        print("\nCreating buy transactions:")
        for symbol, quantity, price in transactions:
            conn.execute(text("""
                INSERT INTO transactions 
                (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
                VALUES (:portfolio_id, :stock_id, 'BUY', :quantity, :price, :date)
            """), {
                "portfolio_id": portfolio_id,
                "stock_id": stocks[symbol],
                "quantity": quantity,
                "price": price,
                "date": buy_date
            })
            print(f"  ✓ BUY {quantity} {symbol} @ ${price}")
        
        # Add some sell transactions (5 days ago)
        sell_date = datetime.now() - timedelta(days=5)
        sells = [
            ('AAPL', 20, 173.00),
            ('TSLA', 10, 238.00),
        ]
        
        print("\nCreating sell transactions:")
        for symbol, quantity, price in sells:
            conn.execute(text("""
                INSERT INTO transactions 
                (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
                VALUES (:portfolio_id, :stock_id, 'SELL', :quantity, :price, :date)
            """), {
                "portfolio_id": portfolio_id,
                "stock_id": stocks[symbol],
                "quantity": quantity,
                "price": price,
                "date": sell_date
            })
            print(f"  ✓ SELL {quantity} {symbol} @ ${price}")
        
        conn.commit()
        
        # Show current holdings
        print("\n" + "=" * 60)
        print("Current Portfolio Holdings:")
        print("=" * 60)
        
        result = conn.execute(text("""
            WITH holdings AS (
                SELECT 
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
                GROUP BY s.symbol
            ),
            latest_prices AS (
                SELECT DISTINCT ON (stock_id)
                    stock_id,
                    close as current_price
                FROM stock_prices
                ORDER BY stock_id, timestamp DESC
            )
            SELECT 
                h.symbol,
                h.total_quantity as quantity,
                ROUND(h.total_cost / h.total_quantity, 2) as avg_cost,
                ROUND(lp.current_price, 2) as current_price,
                ROUND(h.total_quantity * lp.current_price, 2) as market_value,
                ROUND((lp.current_price - (h.total_cost / h.total_quantity)) * h.total_quantity, 2) as unrealized_pnl
            FROM holdings h
            JOIN stocks s ON s.symbol = h.symbol
            JOIN latest_prices lp ON lp.stock_id = s.id
            WHERE h.total_quantity > 0
            ORDER BY h.symbol
        """), {"portfolio_id": portfolio_id})
        
        total_cost = 0
        total_value = 0
        
        print(f"{'Symbol':<8} {'Qty':>6} {'Avg Cost':>10} {'Current':>10} {'Market Val':>12} {'Unreal P/L':>12}")
        print("-" * 60)
        
        for row in result:
            symbol, qty, avg_cost, current, value, pnl = row
            total_cost += avg_cost * qty
            total_value += value
            pnl_pct = (pnl / (avg_cost * qty)) * 100
            print(f"{symbol:<8} {qty:>6} ${avg_cost:>9.2f} ${current:>9.2f} ${value:>11.2f} ${pnl:>10.2f} ({pnl_pct:+.1f}%)")
        
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost) * 100 if total_cost > 0 else 0
        
        print("-" * 60)
        print(f"{'TOTAL':<8} {'':<6} ${total_cost:>9.2f} {'':<10} ${total_value:>11.2f} ${total_pnl:>10.2f} ({total_pnl_pct:+.1f}%)")
        print("=" * 60)


if __name__ == "__main__":
    main()
