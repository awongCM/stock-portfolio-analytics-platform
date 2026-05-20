# AI Copilot Instructions - Portfolio Analytics Platform

## Project Overview

**Purpose**: Data analytics platform for stock portfolio performance evaluation combining operational data (PostgreSQL/TimescaleDB) with analytical data lake (Apache Iceberg) capabilities.

**Architecture**: Three-tier system with PostgreSQL for OLTP, MinIO for object storage, and Spark/Iceberg for OLAP analytics.

## Critical Architecture Patterns

### 1. Dual-Database Strategy

- **PostgreSQL/TimescaleDB** (`src/utils/supabase_client.py`): Operational data, real-time transactions, portfolios, stocks
  - Accessed via SQLAlchemy for type-safe queries
  - Uses `.env` / `.env.local` for connection strings
  - Default: `postgresql://postgres:postgres@localhost:5432/portfolio`
- **Apache Iceberg** (`src/iceberg/`): Historical analytics, immutable append-only tables, versioned data
  - Tables in `portfolio_catalog.portfolio` namespace
  - 4 core tables: `stock_prices`, `transactions`, `portfolio_metrics`, `technical_indicators`
  - Partitioned by `stock_symbol` and date for query efficiency

### 2. Spark-Iceberg Integration Pattern

```python
# Every analytics operation follows this pattern:
from src.iceberg.catalog import IcebergCatalog
catalog = IcebergCatalog()
spark = catalog.get_spark_session()  # Pre-configured with Iceberg + MinIO credentials
result = spark.sql(f"SELECT * FROM {catalog.catalog_name}.portfolio.stock_prices")
```

Key config in [Dockerfile](Dockerfile#L43-L49): PyIceberg with S3fs for MinIO backend. **Never hardcode credentials** - use environment variables from Docker containers (minioadmin:minioadmin, access via [http://minio:9000](http://minio:9000)).

### 3. ETL Pipeline Architecture (`src/ingestion/etl_pipeline.py`)

1. **Extract**: Yahoo Finance via `yfinance` (5 stocks: AAPL, MSFT, GOOGL, AMZN, TSLA)
2. **Transform**: Clean data, create portfolio transactions
3. **Load**: PostgreSQL for operational use + Iceberg for analytics
4. **Populate**: Sample portfolio with buy/sell transactions (dataclass `ETLConfig` stores config)

## Key Development Workflows

### Setup (First-Time)

```bash
poetry install
chmod +x scripts/*.sh
./scripts/start-services.sh  # Starts: PostgreSQL, MinIO, Spark+Jupyter
```

Then run [notebooks/fix_and_setup_iceberg.ipynb](notebooks/fix_and_setup_iceberg.ipynb) to create Iceberg tables.

### Local Development from Host

```bash
# PostgreSQL connection: localhost:5432 (not container hostname)
# Set POSTGRES_HOST=localhost in .env.local before running tests/scripts
# Jupyter Lab: http://localhost:8888
# MinIO Console: http://localhost:9001 (minioadmin:minioadmin)
```

### Running Tests

```bash
poetry run pytest                              # All unit tests
poetry run pytest -m integration               # Requires running services
poetry run pytest --cov=src --cov-report=html # Coverage report
```

Test fixtures in [conftest.py](tests/conftest.py); use `pytest-mock` for mocking Spark/DB calls.

## Project-Specific Conventions

### Module Organization

- `src/ingestion/`: Stock data fetching and pipeline orchestration
- `src/iceberg/`: Catalog initialization, schema definitions, table management
- `src/analytics/`: Performance metrics (`portfolio_performance.py`), technical indicators (`technical_indicators.py`)
- `src/utils/`: `supabase_client.py` centralizes all DB connections

### Naming & Data Types

- **Stocks**: Always use uppercase ticker symbols (e.g., "AAPL", not "aapl")
- **Schemas**: Use `pyiceberg.types` (DecimalType for money, TimestampType for dates) - see [schemas.py](src/iceberg/schemas.py)
- **Portfolio IDs**: UUIDs stored as strings in both PostgreSQL and Iceberg

### Error Handling Pattern

```python
# Typical pattern from init-iceberg.py
try:
    catalog.create_namespace(namespace)
except Exception as e:
    print(f"Namespace may already exist: {e}")
```

Non-blocking on repeated setup operations (idempotent design).

### Logging

```python
import logging
logger = logging.getLogger(__name__)
logger.info("Operation completed")  # See etl_pipeline.py line 11-15
```

All infrastructure components log to stdout (captured by docker logs).

## Integration Points & Dependencies

### External Services (Docker Compose)


| Service      | Container Host | Local Port | Credentials           | Purpose                            |
| ------------ | -------------- | ---------- | --------------------- | ---------------------------------- |
| PostgreSQL   | postgres:5432  | 5432       | postgres:postgres     | Operational DB                     |
| MinIO        | minio:9000     | 9000,9001  | minioadmin:minioadmin | S3-compatible object storage       |
| Spark Master | spark:7077     | 8080,4040  | None                  | Distributed computing + Jupyter UI |


### Python Dependencies (pyproject.toml)

- `pyspark` 3.5.0: Analytics engine
- `pyiceberg` 0.6.0: Iceberg table management
- `supabase` 2.3.4: Client SDK (optional, direct PostgreSQL via sqlalchemy preferred)
- `yfinance` 0.2.55: Stock data source
- `sqlalchemy` 2.0.25: Type-safe DB queries

## Common Development Tasks

### Add a New Analytics Metric

1. Create method in [PortfolioAnalyzer](src/analytics/portfolio_performance.py) using Spark SQL
2. Query from Iceberg: `spark.sql(f"SELECT * FROM {self.catalog_name}.portfolio.stock_prices")`
3. Return as PySpark DataFrame
4. Add integration test in [test_analytics.py](tests/test_analytics.py)

### Ingest New Stock Symbol

1. Add to `ETLConfig.symbols` in `scripts/` or Jupyter notebook
2. Iceberg partitions automatically by symbol (`stock_prices` table partitioned)
3. Historical data fetched fresh from Yahoo Finance each run

### Debug Iceberg Issues

1. Check MinIO buckets: `http://localhost:9001` → navigate `iceberg-warehouse/`
2. Query Iceberg table status: Use Jupyter notebook with `spark.sql("SELECT * FROM portfolio_catalog.portfolio.stock_prices LIMIT 1")`
3. Restart services: `docker-compose restart`

## Configuration & Validation with Pydantic

**⚠️ Known Gap**: Pydantic is declared as a dependency (`pydantic` 2.5.3, `pydantic-settings` 2.1.0) but currently unused. Configuration uses `@dataclass` and manual `os.getenv()` parsing instead.

### Where to Apply Pydantic When Extending

**1. Environment Configuration** - Use `pydantic-settings` in [src/utils/supabase_client.py](src/utils/supabase_client.py):

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class DatabaseSettings(BaseSettings):
    postgres_host: str = Field(default="localhost", description="PostgreSQL hostname")
    postgres_port: int = 5432
    postgres_db: str = "portfolio"
    postgres_user: str = "postgres"
    postgres_password: str

    class Config:
        env_file = ".env.local"
        env_file_encoding = "utf-8"
        case_sensitive = False
```

**2. ETL Configuration Validation** - Replace `@dataclass` in [src/ingestion/etl_pipeline.py](src/ingestion/etl_pipeline.py#L21):

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date

class ETLConfig(BaseModel):
    symbols: list[str] = Field(min_items=1)
    start_date: date
    end_date: date
    portfolio_name: str
    portfolio_description: str
    initial_cash: float = Field(default=100000.0, gt=0)

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
```

**3. Data Models** - When creating API request/response handlers or database result containers, use Pydantic BaseModel for automatic serialization, validation, and IDE support.

### Current Workaround

Configuration currently uses:

- `os.getenv()` with defaults in [supabase_client.py](src/utils/supabase_client.py#L35)
- `@dataclass` for `ETLConfig` in [etl_pipeline.py](src/ingestion/etl_pipeline.py#L21)
- `python-dotenv` for `.env` loading

This works for POC but lacks runtime validation. Migrate to Pydantic when adding configuration validation or when creating new configuration classes.

## Testing Patterns

**Fixtures** ([conftest.py](tests/conftest.py)): Mock Spark sessions and DB connections.

**Unit Tests**: Test business logic in isolation (e.g., calculation formulas).

**Integration Tests** (marked with `@pytest.mark.integration`): Require running Docker services; test actual DB and Iceberg reads.

Example from [test_analytics.py](tests/test_analytics.py):

```python
@pytest.mark.integration
def test_portfolio_analyzer_with_iceberg():
    analyzer = PortfolioAnalyzer("test-portfolio")
    transactions = analyzer.get_portfolio_transactions()
    assert transactions.count() > 0
```

## File Locations for Key Patterns


| Pattern                    | File                                                                     |
| -------------------------- | ------------------------------------------------------------------------ |
| Catalog initialization     | [src/iceberg/catalog.py](src/iceberg/catalog.py)                         |
| Table schemas              | [src/iceberg/schemas.py](src/iceberg/schemas.py)                         |
| DB connection (PostgreSQL) | [src/utils/supabase_client.py](src/utils/supabase_client.py#L35)         |
| Setup scripts              | [scripts/](scripts/) (shell wrappers around Python)                      |
| Sample data generation     | [scripts/create-sample-portfolio.py](scripts/create-sample-portfolio.py) |
| Jupyter notebooks          | [notebooks/](notebooks/) (e.g., fix_and_setup_iceberg.ipynb)             |


## Environment Configuration

**Local Development** (`.env.local`):

```bash
POSTGRES_HOST=localhost        # NOT container hostname
POSTGRES_DB=portfolio
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ICEBERG_WAREHOUSE=s3a://iceberg-warehouse/
```

**In Docker Containers**: Hostnames use service names (`postgres`, `minio`, `spark`) and Docker network.

---

**Last Updated**: December 2025