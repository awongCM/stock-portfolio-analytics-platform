---
name: pyspark-iceberg-analytics
description: >-
  Adds or changes PySpark analytics on Apache Iceberg tables in this portfolio
  platform. Use when implementing portfolio metrics, technical indicators, Spark
  SQL queries, DataFrame transforms, PortfolioAnalyzer, TechnicalIndicators, or
  Iceberg reads in src/analytics/.
---

# PySpark + Iceberg analytics

## Prerequisites

- Docker services running: `./scripts/start-services.sh`
- Iceberg tables exist (run `notebooks/fix_and_setup_iceberg.ipynb` or `scripts/init-iceberg.py` via container init)
- Data in lake: `./scripts/run-etl-pipeline.sh` then `./scripts/export-to-iceberg.sh` if tables are empty

## Canonical pattern

```python
from src.iceberg.catalog import IcebergCatalog
from pyspark.sql.functions import col, sum, when
from pyspark.sql.window import Window

catalog = IcebergCatalog()
spark = catalog.get_spark_session()
catalog_name = catalog.catalog_name

df = spark.sql(f"""
    SELECT *
    FROM {catalog_name}.portfolio.stock_prices
    WHERE stock_symbol IN ('AAPL', 'MSFT')
""")
```

Extend existing classes:

- `src/analytics/portfolio_performance.py` — `PortfolioAnalyzer`
- `src/analytics/technical_indicators.py` — `TechnicalIndicators`

## Workflow

```
- [ ] 1. Read existing method in PortfolioAnalyzer / TechnicalIndicators
- [ ] 2. Implement using DataFrame API or spark.sql against portfolio_catalog.portfolio.*
- [ ] 3. Filter early (symbol, date) to reduce shuffle
- [ ] 4. Add unit test with mocked Spark in tests/test_analytics.py
- [ ] 5. Run ./scripts/test-analytics.sh inside portfolio-spark
- [ ] 6. Document Lead takeaway for the user
```

## Table reference

| Table | Typical use |
|-------|-------------|
| `stock_prices` | OHLCV, joins for valuation |
| `transactions` | BUY/SELL, holdings, P&L |
| `portfolio_metrics` | Pre-aggregated metrics |
| `technical_indicators` | RSI, SMA, MACD outputs |

## Conventions

- Tickers: **uppercase** (`AAPL`)
- `portfolio_id`: string UUID, filter in SQL or DataFrame
- Return `DataFrame` from library methods; call `.show()` / `.collect()` only in scripts/tests
- Reuse `Window` specs from `technical_indicators.py` for lag/rolling patterns

## Verify

```bash
./scripts/test-analytics.sh
```

Or in container:

```bash
docker exec portfolio-spark python scripts/test-analytics.py
```

Check Spark UI http://localhost:8080 for job stages if performance matters.

## Lead takeaway (required in response)

After implementation, explain:

1. **Concept** — e.g. window partition, shuffle from `groupBy`
2. **This repo** — which table(s) and class method
3. **Production pitfall** — e.g. full table scan, driver `collect()`, skew on hot symbols

## Anti-patterns

- New `SparkSession.builder` config — use `IcebergCatalog`
- Duplicating catalog name `portfolio_catalog` as a magic string in many files — use `self.catalog_name`
- Large `collect()` or `toPandas()` without limit in pipeline code
