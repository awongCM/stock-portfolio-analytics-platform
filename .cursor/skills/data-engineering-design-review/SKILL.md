---
name: data-engineering-design-review
description: >-
  Reviews data pipeline and lakehouse designs before large implementation in
  the portfolio analytics platform. Use when planning ETL, Iceberg schema changes,
  incremental loads, partitioning, backfills, or when the user asks for a design
  review or architecture decision for PySpark data engineering.
---

# Data engineering design review

Use **before** large diffs (new tables, rewrites, new pipelines). Output the template below; do not jump straight to code unless the user asks.

## Review template

Copy and fill in:

```markdown
## Design review: [feature name]

### 1. Sources & grain
- **Sources:** (e.g. Yahoo Finance, Postgres `stock_prices`)
- **Grain:** one row per ___ (e.g. symbol × day)
- **Keys:** ___

### 2. Storage layers
| Layer | Role in this design |
|-------|---------------------|
| Postgres (OLTP) | |
| Iceberg (lake) | |
| Why both / skip one? | |

### 3. Partitioning & layout
- **Partition columns:** ___
- **Sort / clustering (if any):** ___
- **Expected query filters:** ___

### 4. Incremental strategy
- **Full reload / append / merge:** ___
- **Watermark / CDC column:** ___
- **Idempotency:** how reruns behave ___

### 5. Transform (PySpark)
- **Session:** `IcebergCatalog.get_spark_session()` only
- **Shuffle risk:** groupBy / join keys ___
- **Window / state:** ___

### 6. Quality & tests
- **Row-count / null checks:** ___
- **Unit tests:** mock Spark in `tests/`
- **Integration:** `@pytest.mark.integration` + Docker ___

### 7. Operations
- **Schedule / trigger:** manual script / notebook / future orchestrator
- **Backfill:** ___
- **Failure recovery:** ___
- **Observability:** logs, Spark UI, MinIO inspection

### 8. Risks & alternatives
| Risk | Mitigation |
|------|------------|
| | |

### 9. Repo touch list
- Files to change: ___
- Scripts to run to verify: `./scripts/...`

### 10. Lead takeaway
One paragraph: what a DE lead would say in a design meeting.
```

## Platform defaults (this repo)

- Catalog `portfolio_catalog`, namespace `portfolio`
- Iceberg tables: `stock_prices`, `transactions`, `portfolio_metrics`, `technical_indicators`
- OLTP first via `PortfolioETLPipeline`; lake via `SupabaseToIcebergExporter` / export scripts
- Local object store: MinIO (`s3a://iceberg-warehouse/`)

## Questions to ask if unclear

1. Is data **operational** (Postgres), **analytical** (Iceberg), or both?
2. What is the **smallest increment** that proves the design (one symbol, one day)?
3. Can we **extend** `PortfolioAnalyzer` / existing ETL instead of new entry points?

## When to approve implementation

- [ ] Grain and keys explicit
- [ ] Partitioning matches filter patterns
- [ ] Idempotent rerun story defined
- [ ] Test plan names concrete files/commands
- [ ] No duplicate Spark catalog configuration

## Lead takeaway (required)

Summarize tradeoffs in plain language suitable for leading a team review—not only implementation steps.
