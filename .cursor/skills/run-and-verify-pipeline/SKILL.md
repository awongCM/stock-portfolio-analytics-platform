---
name: run-and-verify-pipeline
description: >-
  Runs and verifies the portfolio ETL and data population workflow end-to-end.
  Use when populating stock_prices, transactions, portfolio_holdings, empty
  tables, sample data, run-etl-pipeline, export-to-iceberg, or verifying setup.
---

# Run and verify pipeline

## Goal

Confirm OLTP (Postgres) and optionally the lake (Iceberg) have expected data for analytics.

## Quick path (default)

```bash
chmod +x scripts/*.sh
./scripts/start-services.sh

# Populates Postgres: stock_prices, portfolios, transactions, holdings
./scripts/run-etl-pipeline.sh

# Export Postgres → Iceberg (if lake empty)
./scripts/export-to-iceberg.sh

# Spark analytics smoke test
./scripts/test-analytics.sh
```

## ETL options

```bash
# Custom symbols / days / cash
./scripts/run-etl-pipeline.sh --days 60 --cash 250000 --symbols "AAPL MSFT NVDA"
```

Source: `src/ingestion/etl_pipeline.py` (`PortfolioETLPipeline`, `ETLConfig`).

## Verify Postgres (host or docker)

```bash
docker exec portfolio-postgres psql -U postgres -d portfolio -c \
  "SELECT COUNT(*) FROM stock_prices;"
```

```bash
docker exec portfolio-postgres psql -U postgres -d portfolio -c \
  "SELECT COUNT(*) FROM transactions;"
```

## Verify Iceberg (Spark container)

```bash
docker-compose exec spark python3 -c "
import sys
sys.path.append('/opt/spark-apps')
from src.iceberg.catalog import IcebergCatalog
c = IcebergCatalog()
s = c.get_spark_session()
s.sql(f'SHOW TABLES IN {c.catalog_name}.portfolio').show()
for t in ['stock_prices','transactions','portfolio_metrics','technical_indicators']:
    n = s.sql(f'SELECT COUNT(*) AS cnt FROM {c.catalog_name}.portfolio.{t}').collect()[0]['cnt']
    print(f'{t}: {n}')
"
```

Or run `scripts/verify-setup.py` copied into the container (see `scripts/verify-setup.py`).

## Full setup script

```bash
poetry run python scripts/verify-setup.py   # host, needs POSTGRES_HOST=localhost
```

## Checklist

```
- [ ] docker-compose ps — postgres, minio, spark healthy
- [ ] ./scripts/run-etl-pipeline.sh — exit 0, logs show row counts
- [ ] Postgres tables non-zero where expected
- [ ] ./scripts/export-to-iceberg.sh — if analytics reads Iceberg
- [ ] Iceberg SHOW TABLES + COUNT(*) per table
- [ ] ./scripts/test-analytics.sh — exit 0
```

## If something fails

| Symptom | Next step |
|---------|-----------|
| Postgres connection refused | `./scripts/start-services.sh`, check port 5432 |
| Empty Iceberg | Run export script; check MinIO bucket `iceberg-warehouse` at http://localhost:9001 |
| Spark errors | Use skill `debug-spark-iceberg-local` |
| Analytics test fails | Ensure sample portfolio exists: `./scripts/create-sample-portfolio.sh` |

## Lead takeaway

State which layer failed (extract / OLTP load / lake export / analytics) and what row counts prove success.
