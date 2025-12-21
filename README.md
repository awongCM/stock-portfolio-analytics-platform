# Supabase + Apache Iceberg Portfolio Analytics

A modern data analytics platform combining PostgreSQL/TimescaleDB for operational data and Apache Iceberg for analytical workloads, focused on portfolio stock performance evaluation.

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   PostgreSQL    │         │  Apache Iceberg  │         │   PySpark       │
│   TimescaleDB   │────────▶│  Data Lake       │────────▶│   Analytics     │
│   (Operational) │         │  (S3/MinIO)      │         │   (Jupyter)     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

## Features

- **Real-time Stock Data**: Store stock prices and portfolio transactions with TimescaleDB optimization
- **Apache Iceberg Integration**: Scalable data lake for historical analytics
- **Performance Analytics**: Portfolio returns, P/L tracking, risk metrics
- **Technical Indicators**: RSI, SMA, MACD, Bollinger Bands
- **Interactive Analysis**: Jupyter notebooks for data exploration

## Tech Stack

- **Database**: PostgreSQL 15 + TimescaleDB 2.11
- **Data Lake**: Apache Iceberg 1.4.3
- **Object Storage**: MinIO (S3-compatible)
- **Processing**: Apache Spark 3.5.0 + PySpark
- **Orchestration**: Docker Compose
- **Language**: Python 3.11+

## Project Structure

```
supabase-iceberg-portfolio/
├── src/
│   ├── ingestion/         # Stock data ingestion (Yahoo Finance)
│   ├── analytics/         # Portfolio performance & technical indicators
│   ├── iceberg/           # Iceberg catalog & table management
│   └── utils/             # Database connections & utilities
├── scripts/               # Setup & helper scripts
├── notebooks/             # Jupyter notebooks for analysis
│   ├── fix_and_setup_iceberg.ipynb    # Setup Iceberg tables
│   └── verify_iceberg_tables.ipynb    # Verify setup
├── supabase/
│   └── migrations/        # Database schema migrations
├── tests/                 # Test suite
├── docker-compose.yaml    # Infrastructure definition
└── pyproject.toml         # Python dependencies
```

## Quick Start

### Prerequisites

- **Docker Desktop** (v20.10+)
- **Docker Compose** (v2.0+)
- **Python** 3.11+
- **Poetry** (Python dependency management)

### Setup (5 minutes)

1. **Install Python dependencies**

   ```bash
   poetry install
   ```

2. **Start all services**

   ```bash
   chmod +x scripts/*.sh
   ./scripts/start-services.sh
   ```

   This starts:

   - Supabase PostgreSQL + TimescaleDB (port 5432)
   - MinIO object storage (ports 9000, 9001)
   - Spark + Jupyter (ports 8080, 8888)

   Wait ~30 seconds for services to be ready.

3. **Setup Iceberg tables**

   Open JupyterLab at http://localhost:8888 and run:

   - `notebooks/fix_and_setup_iceberg.ipynb` (one-time setup)

   This creates the `portfolio` namespace with 4 Iceberg tables.

4. **Generate sample data**

   ```bash
   # Insert 30 days of stock prices (AAPL, MSFT, GOOGL, AMZN, TSLA)
   ./scripts/insert-sample-data.sh

   # Create a sample portfolio with transactions
   ./scripts/create-sample-portfolio.sh
   ```

5. **Verify everything works**

   ```bash
   ./scripts/test-analytics.sh
   ```

## Development Workflow

### 1. Data Ingestion

#### Option A: ETL Pipeline (Recommended - Populates All Tables)

```bash
# Run complete ETL pipeline - populates stock_prices, transactions, holdings
./scripts/run-etl-pipeline.sh

# Customize configuration
./scripts/run-etl-pipeline.sh --days 60 --cash 250000 --symbols "AAPL MSFT NVDA"

# Or use Jupyter notebook
# Open: http://localhost:8888
# Run: notebooks/run_etl_pipeline.ipynb
```

**What it does:**

- ✅ Fetches stock prices from Yahoo Finance (stock_prices table)
- ✅ Creates a portfolio (portfolios table)
- ✅ Generates realistic transactions (transactions table)
- ✅ Auto-calculates holdings (portfolio_holdings table)
- ✅ Validates data integrity

#### Option B: Manual Scripts (Separate Steps)

```bash
# Step 1: Insert stock prices only
./scripts/insert-sample-data.sh

# Step 2: Create portfolio with transactions
./scripts/create-sample-portfolio.sh

# Or use Python API directly
poetry run python -c "
from src.ingestion.stock_ingestion import StockDataIngestion
ingestion = StockDataIngestion()
ingestion.ingest_multiple_stocks(
    symbols=['AAPL', 'MSFT', 'GOOGL'],
    start_date='2024-01-01',
    end_date='2024-01-31'
)
"
```

### 2. Portfolio Management

```bash
# Create portfolio with sample transactions
./scripts/create-sample-portfolio.sh

# Or via SQL
docker exec -it portfolio-postgres psql -U postgres -d portfolio
```

```sql
-- Create portfolio
INSERT INTO portfolios (name, description)
VALUES ('Tech Growth', 'Technology stocks portfolio')
RETURNING id;

-- Add transactions
INSERT INTO transactions (portfolio_id, stock_id, transaction_type, quantity, price, transaction_date)
SELECT 'portfolio-uuid', id, 'BUY', 10, 150.00, NOW()
FROM stocks WHERE symbol = 'AAPL';
```

### 3. Analytics & Visualization

Open **JupyterLab** at http://localhost:8888:

```python
import sys
sys.path.append('/opt/spark-apps')

from src.analytics.portfolio_performance import PortfolioAnalyzer
from src.analytics.technical_indicators import TechnicalIndicators

# Analyze portfolio
analyzer = PortfolioAnalyzer()
performance = analyzer.calculate_portfolio_performance('portfolio-uuid')

# Calculate technical indicators
indicators = TechnicalIndicators()
rsi = indicators.calculate_rsi('AAPL', period=14)
```

### 4. Query Iceberg Tables

In Jupyter notebooks:

```python
from src.iceberg.catalog import IcebergCatalog

catalog = IcebergCatalog()
spark = catalog.get_spark_session()

# Query stock prices
df = spark.sql("""
    SELECT *
    FROM portfolio_catalog.portfolio.stock_prices
    WHERE stock_symbol = 'AAPL'
    ORDER BY timestamp DESC
    LIMIT 10
""")
df.show()
```

### 5. Run Tests

```bash
poetry run pytest tests/ -v
```

## Access Points

| Service           | URL                   | Credentials             |
| ----------------- | --------------------- | ----------------------- |
| **Jupyter Lab**   | http://localhost:8888 | No auth                 |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| **Spark UI**      | http://localhost:8080 | -                       |
| **PostgreSQL**    | localhost:5432        | postgres / postgres     |

### Quick Access Commands

```bash
# PostgreSQL
docker exec -it portfolio-postgres psql -U postgres -d portfolio

# View logs
docker-compose logs -f spark
docker-compose logs -f postgres

# Stop services
./scripts/stop-services.sh

# Restart services
docker-compose restart
```

## Iceberg Tables

After setup, these tables are available in `portfolio_catalog.portfolio`:

| Table                  | Purpose                                     | Partitioning          |
| ---------------------- | ------------------------------------------- | --------------------- |
| `stock_prices`         | Historical stock prices                     | By date and symbol    |
| `transactions`         | Portfolio buy/sell transactions             | By date and portfolio |
| `portfolio_metrics`    | Performance metrics (returns, Sharpe ratio) | By date and portfolio |
| `technical_indicators` | RSI, MACD, SMA, Bollinger Bands             | By date and symbol    |

## What's Working ✅

- ✅ PostgreSQL + TimescaleDB for time-series data
- ✅ Sample data generation (30 days × 5 stocks)
- ✅ Portfolio management with transactions
- ✅ Performance analytics (returns, P/L)
- ✅ Technical indicators (RSI, SMA, Bollinger Bands)
- ✅ Apache Iceberg tables in MinIO
- ✅ Jupyter notebooks for interactive analysis
- ✅ Docker Compose orchestration

## Troubleshooting

### Iceberg Connection Issues

If you see `NoClassDefFoundError: com/amazonaws/AmazonClientException`:

Run the fix notebook: `notebooks/fix_and_setup_iceberg.ipynb`

This downloads the missing AWS SDK JAR and recreates tables.

### Services Won't Start

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Reset everything
docker-compose down -v
docker-compose up -d
```

### Database Connection

```bash
# Test PostgreSQL
docker exec portfolio-postgres pg_isready -U postgres

# Check data
docker exec portfolio-postgres psql -U postgres -d portfolio -c "SELECT COUNT(*) FROM stocks;"
```

## Next Steps

1. **Connect live data**: Integrate Yahoo Finance API for real-time data
2. **Advanced analytics**: Implement risk metrics (VaR, max drawdown)
3. **Dashboards**: Build visualization dashboards
4. **Optimization**: Portfolio optimization algorithms
5. **Backtesting**: Historical strategy backtesting

## License

MIT
