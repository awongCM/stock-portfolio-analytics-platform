# Agent guide — Stock Portfolio Analytics Platform

Onboarding for humans and AI assistants. **Primary goal:** build PySpark + lakehouse skills to lead data engineering projects. Prefer teaching and verification over speed-only changes.

## Read first

**Doc layering:** This file is the entry point (~1 screen). For implementation details (schemas, services, Pydantic gap, integration points), read [.github/copilot-instructions.md](.github/copilot-instructions.md) before editing `src/`. Human ops: [README.md](README.md), [QUICK_REFERENCE.md](QUICK_REFERENCE.md), [GETTING_STARTED.md](GETTING_STARTED.md).


| Doc                                                                | Purpose                                                           |
| ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | **Deep reference** — architecture, conventions, schemas, testing  |
| [README.md](README.md)                                             | Quick start, project layout                                       |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md)                           | Commands, URLs, SQL snippets                                      |
| [GETTING_STARTED.md](GETTING_STARTED.md)                           | First-time setup                                                  |
| [architecture.drawio](architecture.drawio)                         | Data flow diagram                                                 |
| [.cursor/rules/](.cursor/rules/)                                   | File-scoped conventions (auto-apply when matching paths are open) |


## Stack

- **OLTP:** PostgreSQL 15 + TimescaleDB (port 5432)
- **Lake:** Apache Iceberg 1.4.3 on MinIO (S3-compatible)
- **Compute:** Apache Spark 3.5 + PySpark (Docker `portfolio-spark`)
- **Python:** 3.11+, Poetry (`pyproject.toml`)

## Data flow

```text
Yahoo Finance → ingestion (Postgres) → optional export → Iceberg on MinIO → PySpark analytics
```

## Runtime: host vs container


| Context                                              | Postgres host                     | Spark / Iceberg                                |
| ---------------------------------------------------- | --------------------------------- | ---------------------------------------------- |
| **Host** (`poetry run pytest`, local scripts)        | `localhost` — set in `.env.local` | Not available unless you point at remote Spark |
| **Docker** (`portfolio-spark`, `portfolio-postgres`) | `postgres`                        | `minio`, catalog via `IcebergCatalog`          |


**Spark session:** always use `IcebergCatalog().get_spark_session()` from `src/iceberg/catalog.py`. Do not duplicate Spark/Iceberg/S3A config.

```python
from src.iceberg.catalog import IcebergCatalog

catalog = IcebergCatalog()
spark = catalog.get_spark_session()
spark.sql(f"SELECT * FROM {catalog.catalog_name}.portfolio.stock_prices LIMIT 5").show()
```

## Module map


| Path             | Role                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| `src/ingestion/` | yfinance ETL, Postgres load, Iceberg export                                                      |
| `src/iceberg/`   | Catalog, schemas, table management                                                               |
| `src/analytics/` | `PortfolioAnalyzer`, `TechnicalIndicators` (PySpark on Iceberg)                                  |
| `src/utils/`     | `supabase_client.py` — DB connections                                                            |
| `scripts/`       | Shell wrappers — prefer these over ad-hoc commands                                               |
| `notebooks/`     | Jupyter at [http://localhost:8888](http://localhost:8888) (`sys.path.append('/opt/spark-apps')`) |


## Iceberg contract

- **Catalog:** `portfolio_catalog`
- **Namespace:** `portfolio`
- **Tables:** `stock_prices`, `transactions`, `portfolio_metrics`, `technical_indicators`
- **Tickers:** uppercase (e.g. `AAPL`)
- Setup is **idempotent** (namespace/table create may no-op on repeat)

## Commands

```bash
# Setup
poetry install
chmod +x scripts/*.sh
./scripts/start-services.sh

# Populate OLTP + sample portfolio
./scripts/run-etl-pipeline.sh

# Export Postgres → Iceberg (when lake is empty)
./scripts/export-to-iceberg.sh

# Verify analytics in Spark container
./scripts/test-analytics.sh

# Tests (host)
poetry run pytest
poetry run pytest -m integration   # requires Docker services up
```

**UIs:** Spark [http://localhost:8080](http://localhost:8080) · Jupyter [http://localhost:8888](http://localhost:8888) · MinIO [http://localhost:9001](http://localhost:9001)

## Agent behavior (learning mode)

1. **Teach by default** — After changes, add a short **Lead takeaway** (concept, how this repo implements it, production pitfall).
2. **Extend existing code** — Prefer `PortfolioAnalyzer`, `IcebergCatalog`, `PortfolioETLPipeline` over new one-off scripts.
3. **Verify Spark/Iceberg in Docker** — Host unit tests alone are not enough for analytics changes.
4. **Use project skills** — See [.cursor/skills/](.cursor/skills/) for runbooks (invoke by name or when the task matches the skill description):
  - `pyspark-iceberg-analytics` — new metrics / Spark SQL
  - `run-and-verify-pipeline` — ETL, sample data, row counts
  - `debug-spark-iceberg-local` — MinIO, catalog, JAR issues
  - `data-engineering-design-review` — design before large diffs
  - `extend-etl-symbol` — add tickers, date range, `ETLConfig`
  - `iceberg-export-incremental` — Postgres → Iceberg export, append vs replace


| Goal                           | Skill                            |
| ------------------------------ | -------------------------------- |
| Analytics in `src/analytics/`  | `pyspark-iceberg-analytics`      |
| Empty tables / pipeline check  | `run-and-verify-pipeline`        |
| Spark / MinIO / catalog errors | `debug-spark-iceberg-local`      |
| Schema or incremental design   | `data-engineering-design-review` |
| New symbol or ETL config       | `extend-etl-symbol`              |
| Lake export / incremental load | `iceberg-export-incremental`     |


## Extension checklist (analytics)

1. Add method on `PortfolioAnalyzer` or `TechnicalIndicators` in `src/analytics/`
2. Read from `{catalog_name}.portfolio.<table>` via Spark SQL or DataFrame API
3. Unit test with mocked Spark (`tests/test_analytics.py`)
4. Optional `@pytest.mark.integration` when Docker is up
5. Run `./scripts/test-analytics.sh` or prove in a notebook

## Sensitive areas

- Do not hardcode MinIO credentials — use env vars / Docker defaults
- Do not rename catalog, namespace, or core table names without migration plan
- Avoid `collect()` on large DataFrames in production-style code
- f-string SQL with `portfolio_id` is acceptable in POC; prefer temp views / parameters when hardening

## Curriculum map (repo → leadership skills)


| Repo area                        | Competency                               |
| -------------------------------- | ---------------------------------------- |
| `etl_pipeline.py`                | Batch ETL, validation, logging           |
| `iceberg_exporter.py`            | JDBC read, lake load, incremental design |
| `catalog.py` / `init-iceberg.py` | Catalogs, warehouse, S3A                 |
| `portfolio_performance.py`       | Spark SQL, windows, aggregations         |
| `technical_indicators.py`        | Stateful analytics, `Window` specs       |
| Docker + `scripts/`              | Local pipeline ops, reproducible runs    |


## Git commits

Avoid “nothing was committed” confusion: `**git status` = backlog**, `**git log` = already done**. They can both be true.

### When the user asks to commit or push

1. **Scope explicitly** — Stage only paths they name, only files changed in this session, or everything in `git status` if they say “commit all” / “everything pending”. Do not silently exclude dirty files unless they asked to.
2. **Never claim success from `git status` alone** — After commit/push, always report:
  - `git log -1 --oneline --stat` (what landed)
  - `git status -sb` (what remains, if anything)
  - Three lists: **committed**, **left unstaged**, **untracked**
3. **Do not say “nothing to commit”** without both: (a) last commit hash and files, and (b) any remaining modified/untracked paths.
4. **Separate batches** — Agent-created files (e.g. `AGENTS.md`, `.cursor/`) and doc/formatting edits are often different commits; say which batch you are committing.

### Example user prompts

```text
Commit and push only: AGENTS.md, .cursor/skills/
List other dirty files but do not include them.
```

```text
Commit and push everything currently in git status.
```

### After push

Confirm push ref (e.g. `origin/main` at `<hash>`) or show `Everything up-to-date` only when `git status` is clean.