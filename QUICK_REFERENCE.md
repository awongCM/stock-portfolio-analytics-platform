# Quick Reference

## Common Commands

### Start/Stop Services

```bash
# Start all services
./scripts/start-services.sh

# Stop services
./scripts/stop-services.sh

# Restart a service
docker-compose restart spark
docker-compose restart postgres

# Check status
docker-compose ps
```

### Data Management

```bash
# Insert sample stock data (30 days)
./scripts/insert-sample-data.sh

# Create sample portfolio
./scripts/create-sample-portfolio.sh

# Run analytics test
./scripts/test-analytics.sh
```

### Database Access

```bash
# PostgreSQL CLI
docker exec -it portfolio-postgres psql -U postgres -d portfolio

# Check database health
docker exec portfolio-postgres pg_isready -U postgres

# View stock data
docker exec portfolio-postgres psql -U postgres -d portfolio -c "SELECT * FROM stocks;"
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f spark
docker-compose logs -f postgres
docker-compose logs -f minio

# Last 100 lines
docker-compose logs --tail=100 spark
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| **Jupyter Lab** | http://localhost:8888 | No authentication |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Spark Master UI** | http://localhost:8080 | - |
| **PostgreSQL** | localhost:5432 | postgres / postgres |

## SQL Quick Queries

### View Stocks

```sql
SELECT * FROM stocks ORDER BY symbol;
```

### Check Stock Prices

```sql
SELECT s.symbol, sp.timestamp, sp.close, sp.volume
FROM stock_prices sp
JOIN stocks s ON sp.stock_id = s.id
WHERE s.symbol = 'AAPL'
ORDER BY sp.timestamp DESC
LIMIT 10;
```

### View Portfolios

```sql
SELECT p.name, COUNT(t.id) as transactions,
       SUM(CASE WHEN t.transaction_type = 'BUY' 
           THEN t.quantity * t.price ELSE 0 END) as invested
FROM portfolios p
LEFT JOIN transactions t ON p.id = t.portfolio_id
GROUP BY p.id, p.name;
```

### Portfolio Holdings

```sql
SELECT p.name, s.symbol, ph.quantity, ph.average_cost,
       (ph.quantity * ph.average_cost) as total_cost
FROM portfolio_holdings ph
JOIN portfolios p ON ph.portfolio_id = p.id
JOIN stocks s ON ph.stock_id = s.id
ORDER BY p.name, s.symbol;
```

## Python Quick Start

### In Jupyter Notebook

```python
import sys
sys.path.append('/opt/spark-apps')

# Database connection
from src.utils.supabase_client import SupabaseConnection
conn = SupabaseConnection()
engine = conn.get_postgres_engine()

# Query with pandas
import pandas as pd
df = pd.read_sql("SELECT * FROM stocks", engine)
print(df)

# Portfolio analytics
from src.analytics.portfolio_performance import PortfolioAnalyzer
analyzer = PortfolioAnalyzer()
performance = analyzer.calculate_portfolio_performance('portfolio-uuid')

# Technical indicators
from src.analytics.technical_indicators import TechnicalIndicators
indicators = TechnicalIndicators()
rsi = indicators.calculate_rsi('AAPL', period=14)
```

### Iceberg Queries

```python
from src.iceberg.catalog import IcebergCatalog

catalog = IcebergCatalog()
spark = catalog.get_spark_session()

# Query Iceberg table
df = spark.sql("""
    SELECT stock_symbol, timestamp, close 
    FROM portfolio_catalog.portfolio.stock_prices 
    WHERE stock_symbol = 'AAPL'
    ORDER BY timestamp DESC
    LIMIT 10
""")
df.show()
```

## Troubleshooting

### Services Not Starting

```bash
# Reset and rebuild
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Iceberg Connection Errors

Run the fix notebook:
```
Open: http://localhost:8888
Run: notebooks/fix_and_setup_iceberg.ipynb
```

### Database Connection Issues

```bash
# Test connection
docker exec portfolio-postgres pg_isready -U postgres

# Restart PostgreSQL
docker-compose restart postgres
```

## Useful Docker Commands

```bash
# Execute command in container
docker exec portfolio-spark python3 /opt/spark-apps/your-script.py

# Copy files to/from container
docker cp local-file.py portfolio-spark:/tmp/
docker cp portfolio-spark:/tmp/output.txt ./

# Shell access
docker exec -it portfolio-spark bash
docker exec -it portfolio-postgres bash

# Clean up
docker-compose down -v  # Remove all data
docker system prune -a  # Clean up everything
```

## Development Workflow

1. **Make code changes** in `src/` directory
2. **Test in Jupyter** at http://localhost:8888
3. **Run unit tests**: `poetry run pytest tests/`
4. **View logs** for debugging
5. **Commit changes** when working

See [README.md](README.md) for detailed documentation.

```bash
docker-compose exec postgres psql -U postgres -d portfolio
```

#### Spark Shell

```bash
docker-compose exec spark spark-shell
```

#### PySpark

```bash
docker-compose exec spark pyspark
```

## Quick Scripts

### 1. Run Analytics

```bash
./scripts/test-analytics.sh
```

Shows portfolio performance and technical indicators.

### 2. Generate Sample Data

```bash
./scripts/insert-sample-data.sh
```

Creates 30 days of stock prices for 5 symbols.

### 3. Create Portfolio

```bash
./scripts/create-sample-portfolio.sh
```

Generates portfolio with buy/sell transactions.

## Python Examples (in JupyterLab)

### Query Data

```python
import sys
sys.path.append('/opt/spark-apps')
from src.utils.supabase_client import get_postgres_engine
import pandas as pd

engine = get_postgres_engine()
df = pd.read_sql("SELECT * FROM stocks", engine)
print(df)
```

### Calculate Technical Indicators

```python
from sqlalchemy import text
import pandas as pd

engine = get_postgres_engine()
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT timestamp::date, close
        FROM stock_prices sp
        JOIN stocks s ON sp.stock_id = s.id
        WHERE s.symbol = 'AAPL'
        ORDER BY timestamp
    """))
    df = pd.DataFrame(result.fetchall(), columns=['date', 'close'])

# Calculate SMA
df['sma_14'] = df['close'].rolling(14).mean()
print(df.tail())
```

## Troubleshooting

### Services Won't Start

```bash
# Clean up and restart
docker-compose down -v
docker system prune -f
./scripts/start-services.sh
```

### Port Already in Use

```bash
# Find process using port (example: 5432)
lsof -i :5432

# Kill the process
kill -9 <PID>
```

### Can't Connect to Database

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready -U postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Python Import Errors

```bash
# Reinstall dependencies
cd /Users/andywongcheeming/Projects/poc/supabase-iceberg-portfolio
poetry install
```

## Database Schema

### Key Tables

| Table                 | Description                     |
| --------------------- | ------------------------------- |
| `portfolios`          | User portfolios                 |
| `stocks`              | Stock metadata                  |
| `stock_prices`        | Historical prices (TimescaleDB) |
| `transactions`        | Buy/sell transactions           |
| `portfolio_holdings`  | Current positions               |
| `portfolio_snapshots` | Historical performance          |

### Common Queries

```sql
-- View all stocks
SELECT * FROM stocks;

-- Recent prices
SELECT s.symbol, sp.timestamp, sp.close
FROM stock_prices sp
JOIN stocks s ON sp.stock_id = s.id
ORDER BY sp.timestamp DESC
LIMIT 100;

-- Portfolio holdings
SELECT
    p.name,
    s.symbol,
    ph.quantity,
    ph.average_cost
FROM portfolio_holdings ph
JOIN portfolios p ON ph.portfolio_id = p.id
JOIN stocks s ON ph.stock_id = s.id;
```

## Environment Variables

Located in `.env` file:

```bash
# Supabase
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your-key

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=portfolio
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Iceberg
ICEBERG_CATALOG=portfolio_catalog
ICEBERG_WAREHOUSE=s3a://iceberg-warehouse/
```

## Jupyter Notebooks

### Start Jupyter Lab

Already running at http://localhost:8888

### Available Notebooks

- `notebooks/portfolio_analysis.ipynb` - Main analysis workflow

### Create New Notebook

1. Open http://localhost:8888
2. Click "New" → "Python 3"
3. Import modules:
   ```python
   import sys
   sys.path.append('/opt/spark-apps')
   from src.utils.supabase_client import *
   ```

## Current Data Storage

### PostgreSQL (Active)

All data currently stored and queried via PostgreSQL + TimescaleDB:

- `stocks` - Stock metadata
- `stock_prices` - Time-series price data (TimescaleDB hypertable)
- `portfolios` - User portfolios
- `transactions` - Buy/sell records

### Iceberg Tables (Created, S3 Pending)

Iceberg table structure created, S3 access requires AWS SDK JAR:

- `portfolio.stock_prices`
- `portfolio.transactions`
- `portfolio.portfolio_metrics`
- `portfolio.technical_indicators`

To enable: Add AWS SDK bundle JAR to `/opt/spark/jars/`

## Performance Tips

1. **Use TimescaleDB compression** for old data
2. **Partition Iceberg tables** by date and symbol
3. **Batch ingestions** rather than real-time inserts
4. **Cache frequently accessed data** in Spark
5. **Use connection pooling** for database connections

## Support

- Documentation: See `README.md` and `GETTING_STARTED.md`
- Issues: Check Docker logs for errors
- Community: Apache Iceberg, Supabase, PySpark docs
