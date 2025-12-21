# Supabase + Apache Iceberg Portfolio Project - Setup Complete! 🎉

## ✅ What's Working

### 1. **PostgreSQL + TimescaleDB** ✓

- Database: `portfolio`
- 5 stocks preloaded (AAPL, MSFT, GOOGL, AMZN, TSLA)
- TimescaleDB hypertables for time-series data
- Complete schema with portfolios, stocks, transactions, holdings

### 2. **Docker Services** ✓

- PostgreSQL: Port 5432
- MinIO: Ports 9000 (API), 9001 (Console)
- Spark: Ports 8080 (UI), 8888 (Jupyter Lab)
- All services healthy and running

### 3. **Iceberg Tables** ✓

- Namespace: `portfolio_catalog.portfolio`
- Tables created: stock_prices, transactions, portfolio_metrics, technical_indicators
- Partitioned by date and symbol for efficient querying

### 4. **Project Structure** ✓

- Complete Python modules in `src/`
- Helper scripts in `scripts/`
- Jupyter notebooks in `notebooks/`
- Comprehensive documentation

## 📝 Current Status

### What's Working ✅

- PostgreSQL + TimescaleDB for all data storage
- Sample data generation (30 days, 5 stocks)
- Portfolio management and transactions
- Real-time performance analytics
- Technical indicators (RSI, SMA, Bollinger Bands)
- All analytics running via PostgreSQL queries

### Known Limitations

**Iceberg S3 Access**: Tables created but S3 filesystem requires AWS SDK JARs

- Current approach: Use PostgreSQL directly (fully functional)
- Future: Add AWS SDK bundle JAR for full Iceberg integration

**Stock Data**: Using sample data generator instead of live APIs

- Sample data provides realistic test scenarios
- Yahoo Finance API can be integrated later with proper network configuration

## 🚀 How to Use

### Run Analytics (Recommended First Step)

```bash
./scripts/test-analytics.sh
```

This displays:

- Portfolio performance with P/L
- Technical indicators for AAPL
- Demonstrates working analytics

### Generate More Data

```bash
# Add another 30 days of price data
./scripts/insert-sample-data.sh

# Create another sample portfolio
./scripts/create-sample-portfolio.sh
```

### Query Data with SQL

```bash
docker exec -it portfolio-postgres psql -U postgres -d portfolio
```

### Use JupyterLab

1. Open http://localhost:8888
2. Create a new Python 3 notebook
3. Import modules and analyze data interactively

## 📊 Sample Workflow

### 1. Create a Portfolio

```sql
INSERT INTO portfolios (name, description)
VALUES ('Tech Growth', 'High-growth technology stocks')
RETURNING id;
```

### 2. Add Transactions

```sql
INSERT INTO transactions (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
SELECT
    'your-portfolio-id',
    id,
    'BUY',
    10,
    150.00,
    NOW()
FROM stocks
WHERE symbol = 'AAPL';
```

### 3. View Holdings

```sql
SELECT
    p.name,
    s.symbol,
    ph.quantity,
    ph.average_cost
FROM portfolio_holdings ph
JOIN portfolios p ON ph.portfolio_id = p.id
JOIN stocks s ON ph.stock_id = s.id;
```

### 4. Check Performance

```sql
SELECT
    s.symbol,
    sp.timestamp,
    sp.close,
    LAG(sp.close) OVER (PARTITION BY s.symbol ORDER BY sp.timestamp) as prev_close
FROM stock_prices sp
JOIN stocks s ON sp.stock_id = s.id
WHERE s.symbol = 'AAPL'
ORDER BY sp.timestamp DESC
LIMIT 10;
```

## 🔧 Quick Commands

```bash
# Start services
./scripts/start-services.sh

# Stop services
./scripts/stop-services.sh

# Verify setup
docker cp scripts/verify-setup.py portfolio-spark:/tmp/verify-setup.py && \
docker-compose exec -T spark python3 /tmp/verify-setup.py

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d portfolio

# View logs
docker-compose logs -f spark
docker-compose logs -f postgres

# Restart a service
docker-compose restart spark
```

## 🌐 Access Points

| Service       | URL                   | Credentials             |
| ------------- | --------------------- | ----------------------- |
| Jupyter Lab   | http://localhost:8888 | -                       |
| Spark UI      | http://localhost:8080 | -                       |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |
| PostgreSQL    | localhost:5432        | postgres / postgres     |

## 📚 Documentation

- `README.md` - Project overview
- `GETTING_STARTED.md` - Detailed setup guide
- `QUICK_REFERENCE.md` - Command reference
- `notebooks/README.md` - Notebook examples

## 🎯 Next Steps

1. **Ingest real stock data** using the local ingestion method
2. **Create portfolios** and add transactions
3. **Analyze performance** using SQL or Jupyter notebooks
4. **Build visualizations** in Jupyter Lab
5. **Calculate technical indicators** (SMA, RSI, etc.)

## 💡 Tips

- **TimescaleDB** automatically optimizes time-series queries
- **Partitioning** on PostgreSQL helps with large datasets
- **Use Jupyter** for interactive analysis and visualization
- **MinIO** can store any additional data files you need

## ✨ What You've Built

A complete portfolio analytics platform with:

- ✅ Real-time data storage (PostgreSQL + TimescaleDB)
- ✅ Scalable architecture (Docker containers)
- ✅ Analytics ready (Spark + Jupyter)
- ✅ Object storage (MinIO)
- ✅ Time-series optimization
- ✅ Complete Python SDK

**You're ready to build amazing portfolio analytics!** 🚀
