# Why Not All PostgreSQL Tables Are Populated

## Current Database State

### ✅ What's Populated Automatically

When you run `docker-compose up -d`, the database migration file (`supabase/migrations/001_initial_schema.sql`) automatically populates:

#### 1. **Stocks Table** (5 records)
```sql
INSERT INTO stocks (symbol, name, exchange, sector, industry) VALUES
    ('AAPL', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics'),
    ('MSFT', 'Microsoft Corporation', 'NASDAQ', 'Technology', 'Software'),
    ('GOOGL', 'Alphabet Inc.', 'NASDAQ', 'Technology', 'Internet Services'),
    ('AMZN', 'Amazon.com Inc.', 'NASDAQ', 'Consumer Cyclical', 'Internet Retail'),
    ('TSLA', 'Tesla Inc.', 'NASDAQ', 'Consumer Cyclical', 'Auto Manufacturers');
```

#### 2. **Portfolios Table** (2 records)
```sql
INSERT INTO portfolios (name, description) VALUES
    ('Growth Portfolio', 'Focused on high-growth tech stocks'),
    ('Dividend Portfolio', 'Income-generating dividend stocks');
```

### ❌ What's NOT Populated (By Design)

These tables are **intentionally empty** and require manual population:

| Table | Purpose | Why Empty |
|-------|---------|-----------|
| `stock_prices` | Historical price data | Time-series data - too large for migrations |
| `transactions` | Buy/sell transactions | User-specific data |
| `portfolio_holdings` | Current positions | Auto-calculated from transactions |
| `portfolio_snapshots` | Historical snapshots | Generated during analysis |

## Why This Design?

### 1. **Separation of Concerns**
- **Schema migrations** = Database structure + reference data
- **Data scripts** = Large datasets and test data

### 2. **Performance**
- Stock price data can be millions of rows
- Not suitable for SQL migrations
- Should be loaded via efficient batch processes

### 3. **Flexibility**
- Users can choose when and what data to load
- Different environments need different data
- Test data vs. production data

### 4. **Cost & Storage**
- Historical price data is large
- Not everyone needs 30 days of sample data
- Load only what you need for testing

## How to Populate the Empty Tables

### Option 1: Quick Demo (Recommended)

Run the provided scripts to populate with 30 days of sample data:

```bash
# Populate stock_prices (30 days × 5 stocks = ~150 records)
./scripts/insert-sample-data.sh

# Populate transactions + portfolio_holdings (via trigger)
./scripts/create-sample-portfolio.sh
```

**What this gives you:**
- 150 stock price records (30 days × 5 stocks)
- 1 new portfolio ("Tech Growth Portfolio")
- 7 transactions (5 BUY, 2 SELL)
- 3 holdings (auto-calculated)

### Option 2: Custom Data

Use Python API to load specific data:

```python
from src.ingestion.stock_ingestion import StockDataIngestion

ingestion = StockDataIngestion()
ingestion.ingest_multiple_stocks(
    symbols=['AAPL', 'MSFT'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### Option 3: Manual SQL

Insert your own data directly:

```sql
-- Get stock ID
SELECT id FROM stocks WHERE symbol = 'AAPL';

-- Insert price data
INSERT INTO stock_prices (stock_id, timestamp, open, high, low, close, volume, adjusted_close)
VALUES ('stock-uuid', '2024-01-01', 180.0, 185.0, 178.0, 183.0, 50000000, 183.0);

-- Create portfolio
INSERT INTO portfolios (name, description)
VALUES ('My Portfolio', 'Personal investment portfolio')
RETURNING id;

-- Add transaction (automatically updates portfolio_holdings via trigger)
INSERT INTO transactions (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
VALUES ('portfolio-uuid', 'stock-uuid', 'BUY', 10, 183.0, NOW());
```

## Table Relationships

```
stocks (5 records - SEEDED)
   ↓
stock_prices (EMPTY - needs manual load)
   ↓
portfolios (2 records - SEEDED)
   ↓
transactions (EMPTY - needs manual load)
   ↓ (trigger auto-updates)
portfolio_holdings (EMPTY - auto-calculated)
   ↓
portfolio_snapshots (EMPTY - generated on-demand)
```

## Current Table Status

Check what's populated in your database:

```bash
docker exec portfolio-postgres psql -U postgres -d portfolio -c "
SELECT 'stocks' as table_name, COUNT(*) as row_count FROM stocks
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'portfolios', COUNT(*) FROM portfolios
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'portfolio_holdings', COUNT(*) FROM portfolio_holdings;
"
```

**Expected output (before running scripts):**
```
 table_name         | row_count
--------------------+-----------
 stocks             |         5
 stock_prices       |         0
 portfolios         |         2
 transactions       |         0
 portfolio_holdings |         0
```

**Expected output (after running scripts):**
```
 table_name         | row_count
--------------------+-----------
 stocks             |         5
 stock_prices       |       150
 portfolios         |         3
 transactions       |         7
 portfolio_holdings |         3
```

## Summary

✅ **By Design:**
- Schema and reference data (stocks, portfolios) are auto-populated
- Large datasets (prices, transactions) require explicit loading
- This is a **standard practice** for data platforms

✅ **To Get Started:**
1. Run `./scripts/insert-sample-data.sh` - Loads 30 days of prices
2. Run `./scripts/create-sample-portfolio.sh` - Creates portfolio with transactions
3. Run `./scripts/test-analytics.sh` - Verify everything works

✅ **For Production:**
- Use data ingestion pipelines (scheduled jobs)
- Load data incrementally (daily/hourly)
- Use Iceberg for historical data archival
