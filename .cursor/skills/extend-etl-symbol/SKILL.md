---
name: extend-etl-symbol
description: >-
  Adds stock symbols, date ranges, or ETL configuration for the portfolio ETL
  pipeline. Use when adding tickers, changing ETLConfig, run-etl-pipeline.sh
  flags, Yahoo Finance ingest, or populating Postgres stock_prices and transactions.
---

# Extend ETL symbol / config

## Key files

- `src/ingestion/etl_pipeline.py` — `ETLConfig`, `PortfolioETLPipeline`
- `src/ingestion/stock_ingestion.py` — Yahoo Finance ingest
- `scripts/run-etl-pipeline.sh` — CLI (`--days`, `--symbols`, `--cash`, `--portfolio-name`)

## Workflow

```
- [ ] 1. Add symbol(s) uppercase to ETLConfig.symbols or --symbols flag
- [ ] 2. Adjust start_date / end_date or --days in run-etl-pipeline.sh
- [ ] 3. Run ./scripts/run-etl-pipeline.sh
- [ ] 4. Verify Postgres counts (stock_prices, transactions, holdings)
- [ ] 5. If analytics needs lake data: ./scripts/export-to-iceberg.sh
- [ ] 6. Lead takeaway: grain, idempotency on rerun
```

## CLI examples

```bash
./scripts/run-etl-pipeline.sh
./scripts/run-etl-pipeline.sh --days 60 --symbols "AAPL MSFT NVDA" --cash 250000
```

## ETLConfig shape

```python
@dataclass
class ETLConfig:
    symbols: List[str]      # uppercase tickers
    start_date: str
    end_date: str
    portfolio_name: str
    portfolio_description: str
    initial_cash: float = 100000.0
```

## Verify Postgres

```bash
docker exec portfolio-postgres psql -U postgres -d portfolio -c \
  "SELECT symbol FROM stocks ORDER BY symbol;"
docker exec portfolio-postgres psql -U postgres -d portfolio -c \
  "SELECT COUNT(*) FROM stock_prices;"
```

## Notes

- Default symbols: AAPL, MSFT, GOOGL, AMZN, TSLA
- Holdings update via DB triggers after transactions
- Iceberg is **not** populated by ETL alone — run export skill or `export-to-iceberg.sh`

## Deep reference

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for ETL architecture and Pydantic migration notes.
