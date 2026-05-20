# Getting Started

Complete setup guide for the Portfolio Analytics platform.

## Prerequisites

- **Docker Desktop** (v20.10+) and **Docker Compose** (v2.0+)
- **Python** 3.11+
- **Poetry** for dependency management

## Step-by-Step Setup

### 1. Install Dependencies

```bash
poetry install
```

### 2. Start Services

```bash
chmod +x scripts/*.sh
./scripts/start-services.sh
```

Services started:

- PostgreSQL + TimescaleDB (port 5432)
- MinIO object storage (ports 9000, 9001)
- Spark + Jupyter (ports 8080, 8888, 4040)

Wait ~30 seconds for services to be healthy.

### 3. Setup Iceberg Tables

**Option A: Using Jupyter Notebook (Recommended)**

1. Open [http://localhost:8888](http://localhost:8888)
2. Open `notebooks/fix_and_setup_iceberg.ipynb`
3. Run all cells

**Option B: Using Shell Script**

```bash
./scripts/setup-iceberg.sh
```

This creates 4 Iceberg tables in the `portfolio` namespace:

- `stock_prices` - Historical stock data
- `transactions` - Portfolio transactions
- `portfolio_metrics` - Performance metrics
- `technical_indicators` - Technical analysis

### 4. Generate Sample Data

```bash
# Insert 30 days of stock prices for 5 stocks (AAPL, MSFT, GOOGL, AMZN, TSLA)
./scripts/insert-sample-data.sh

# Create a sample portfolio with transactions
./scripts/create-sample-portfolio.sh
```

### 5. Verify Setup

```bash
./scripts/test-analytics.sh
```

You should see:

- Portfolio holdings and P/L
- Technical indicators for AAPL (RSI, SMA, Bollinger Bands)

## Access Services


| Service       | URL                                            | Credentials             |
| ------------- | ---------------------------------------------- | ----------------------- |
| Jupyter Lab   | [http://localhost:8888](http://localhost:8888) | No auth                 |
| MinIO Console | [http://localhost:9001](http://localhost:9001) | minioadmin / minioadmin |
| Spark UI      | [http://localhost:8080](http://localhost:8080) | -                       |


### PostgreSQL Access

```bash
docker exec -it portfolio-postgres psql -U postgres -d portfolio
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f spark
docker-compose logs -f postgres
```

## Troubleshooting

### Iceberg Setup Issues

If you see `NoClassDefFoundError: com/amazonaws/AmazonClientException`:

Run the fix notebook: `notebooks/fix_and_setup_iceberg.ipynb`

### Services Won't Start

```bash
# Check status
docker-compose ps

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Database Connection Issues

```bash
# Test PostgreSQL
docker exec portfolio-postgres pg_isready -U postgres

# Check data
docker exec portfolio-postgres psql -U postgres -d portfolio -c "SELECT COUNT(*) FROM stocks;"
```

## Next Steps

1. Explore sample data in PostgreSQL
2. Open Jupyter notebooks for interactive analysis
3. Query Iceberg tables using Spark SQL
4. Create your own portfolios and transactions
5. Build custom analytics and visualizations

See the main [README.md](README.md) for detailed usage examples.

```

This generates realistic price data for AAPL, MSFT, GOOGL, AMZN, and TSLA.

## Step 6: Create Sample Portfolio

Generate a test portfolio with buy/sell transactions:

```bash
./scripts/create-sample-portfolio.sh
```

This creates a "Tech Growth Portfolio" with transactions and displays current holdings.

## Step 7: Test Analytics

Run the analytics test to verify everything works:

```bash
./scripts/test-analytics.sh
```

You should see:

- Portfolio holdings with P/L calculations
- Technical indicators for AAPL (RSI, SMA, Bollinger Bands)

### Check Services

**MinIO Console**: [http://localhost:9001](http://localhost:9001) (minioadmin/minioadmin)

- Verify `iceberg-warehouse` bucket exists

**JupyterLab**: [http://localhost:8888](http://localhost:8888)

- Open existing notebooks or create new ones

**PostgreSQL**:

```bash
docker exec -it portfolio-postgres psql -U postgres -d portfolio
```

## Next Steps

### Explore Sample Data

The sample portfolio is already set up with:

- 5 stocks (AAPL, MSFT, GOOGL, AMZN, TSLA)
- 30 days of price history
- Buy/sell transactions
- Current holdings with P/L

### Query with SQL

```bash
docker exec -it portfolio-postgres psql -U postgres -d portfolio
```

```sql
-- View portfolio performance
SELECT
    p.name,
    COUNT(t.id) as transactions,
    SUM(CASE WHEN t.transaction_type = 'BUY'
        THEN t.quantity * t.price ELSE 0 END) as invested
FROM portfolios p
LEFT JOIN transactions t ON p.id = t.portfolio_id
GROUP BY p.id, p.name;

-- View stock prices
SELECT
    s.symbol,
    sp.timestamp::date as date,
    sp.close,
    sp.volume
FROM stock_prices sp
JOIN stocks s ON sp.stock_id = s.id
WHERE s.symbol = 'AAPL'
ORDER BY sp.timestamp DESC
LIMIT 10;
```

### Use JupyterLab

Open [http://localhost:8888](http://localhost:8888) and create a notebook:

```python
import sys
sys.path.append('/opt/spark-apps')
from src.utils.supabase_client import get_postgres_engine
import pandas as pd

# Query data
engine = get_postgres_engine()
df = pd.read_sql("""
    SELECT s.symbol, COUNT(*) as price_count
    FROM stock_prices sp
    JOIN stocks s ON sp.stock_id = s.id
    GROUP BY s.symbol
""", engine)
print(df)
```

## Troubleshooting

### Services won't start

```bash
# Check Docker logs
docker-compose logs -f

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Check service health

```bash
# Verify all services are running
docker-compose ps

# Test PostgreSQL
docker exec portfolio-postgres pg_isready -U postgres

# Test database connection
docker exec portfolio-postgres psql -U postgres -d portfolio -c "SELECT COUNT(*) FROM stocks;"
```

### Re-run setup

```bash
# Recreate Iceberg tables
./scripts/setup-iceberg.sh

# Regenerate sample data
./scripts/insert-sample-data.sh
./scripts/create-sample-portfolio.sh
```

## Development Workflow

1. **Modify code** in `src/` directory
2. **Test in Jupyter** at [http://localhost:8888](http://localhost:8888)
3. **Run unit tests**:
  ```bash
   poetry run pytest tests/
  ```
4. **Submit Spark jobs**:
  ```bash
   docker-compose exec spark spark-submit --master local[*] /opt/spark-apps/your_job.py
  ```

## Stopping Services

```bash
./scripts/stop-services.sh
```

Or to remove all data:

```bash
docker-compose down -v
```

## Additional Resources

- [Apache Iceberg Documentation](https://iceberg.apache.org/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [Supabase Documentation](https://supabase.com/docs)
- [TimescaleDB Documentation](https://docs.timescale.com/)

