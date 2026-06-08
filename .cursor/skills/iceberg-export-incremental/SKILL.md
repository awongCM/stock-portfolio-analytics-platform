---
name: iceberg-export-incremental
description: >-
  Exports or incrementally loads data from Postgres to Apache Iceberg via PySpark
  JDBC. Use when export-to-iceberg, SupabaseToIcebergExporter, append vs replace,
  run_incremental_export, or lake sync from OLTP.
---

# Iceberg export and incremental load

## Key files

- `src/ingestion/iceberg_exporter.py` — `SupabaseToIcebergExporter`
- `scripts/export-to-iceberg.sh` — spark-submit wrapper
- `src/iceberg/catalog.py` — `IcebergCatalog.get_spark_session()`

## Current write modes (know before changing)

| Method | Iceberg write | Risk on rerun |
|--------|---------------|---------------|
| `export_stock_prices_to_iceberg` | `createOrReplace` | Replaces table |
| `export_transactions_to_iceberg` | `append` | Duplicates without dedup |
| `run_incremental_export` | date-filtered JDBC read | Uses today 00:00 as watermark (POC) |

## Workflow

```
- [ ] 1. Confirm Postgres has data (run-etl-pipeline or existing rows)
- [ ] 2. Docker up: ./scripts/start-services.sh
- [ ] 3. Run ./scripts/export-to-iceberg.sh
- [ ] 4. Verify counts in Spark (portfolio_catalog.portfolio.*)
- [ ] 5. For design changes: use skill data-engineering-design-review first
- [ ] 6. Lead takeaway: append vs MERGE vs partition overwrite
```

## Verify lake

```bash
docker-compose exec spark python3 -c "
import sys
sys.path.append('/opt/spark-apps')
from src.iceberg.catalog import IcebergCatalog
c = IcebergCatalog()
s = c.get_spark_session()
for t in ['stock_prices','transactions']:
    n = s.sql(f'SELECT COUNT(*) AS cnt FROM {c.catalog_name}.portfolio.{t}').collect()[0]['cnt']
    print(f'{t}: {n}')
"
```

## Incremental pattern (POC)

`run_incremental_export()` filters JDBC by `start_date` since midnight UTC today. Production would use a metadata table for last watermark.

## Hardening direction

- Replace `createOrReplace` with append + merge on `(stock_symbol, timestamp)` for prices
- Store `last_export_ts` in Postgres metadata table
- Partition `stock_prices` by symbol and date (already in schema intent)

## JDBC in container

JDBC URL must use host `postgres:5432` inside `portfolio-spark`, not `localhost`.

## Deep reference

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for dual-database strategy and Iceberg table list.
