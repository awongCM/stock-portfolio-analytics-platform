---
name: debug-spark-iceberg-local
description: >-
  Debugs local Spark, Apache Iceberg, and MinIO issues in the portfolio Docker
  stack. Use when Iceberg tables are empty, catalog errors, S3A failures, Spark
  container won't start, JAR/classpath problems, or MinIO connectivity fails.
---

# Debug Spark + Iceberg (local Docker)

## Service health

```bash
docker-compose ps
docker-compose logs --tail=100 spark
docker-compose logs --tail=50 minio
docker-compose restart spark
```

**URLs**

- Spark Master: http://localhost:8080
- Spark app (when job running): http://localhost:4040
- MinIO console: http://localhost:9001 (minioadmin / minioadmin)
- Jupyter: http://localhost:8888

## MinIO / S3A

1. Open MinIO console → bucket `iceberg-warehouse` (or path from `ICEBERG_WAREHOUSE`)
2. Confirm objects exist under `portfolio/` after export or init
3. In-container endpoint must be `http://minio:9000`, not `localhost`

Env (Docker): `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` — see `src/iceberg/catalog.py`.

## Iceberg catalog

```bash
docker-compose exec spark python3 /opt/spark-apps/scripts/init-iceberg.py
```

Expected namespace: `portfolio` under catalog `portfolio_catalog`.

List tables:

```python
from src.iceberg.catalog import IcebergCatalog
c = IcebergCatalog()
s = c.get_spark_session()
s.sql(f"SHOW TABLES IN {c.catalog_name}.portfolio").show()
```

## Common errors

| Error / symptom | Likely cause | Fix |
|-----------------|--------------|-----|
| `Unknown catalog` | Tables not initialized | `init-iceberg.py`, restart spark |
| `Path does not exist` s3a:// | Empty warehouse or wrong bucket | Run export; check MinIO |
| `ClassNotFoundException` Iceberg | Missing JAR | See `scripts/fix-aws-jars.sh`, Dockerfile `/opt/spark/jars` |
| Connection to `localhost:9000` from container | Wrong host for S3 | Use `minio:9000` inside Docker |
| Postgres JDBC from Spark fails | Wrong JDBC host | Use `postgres:5432` in container, not localhost |

## Re-init sequence

```bash
./scripts/stop-services.sh
./scripts/start-services.sh
# wait ~30s
docker-compose exec spark python3 /opt/spark-apps/scripts/init-iceberg.py
./scripts/export-to-iceberg.sh
./scripts/test-analytics.sh
```

## Shell inside Spark container

```bash
docker exec -it portfolio-spark bash
pyspark   # or spark-shell
```

Python apps need:

```python
import sys
sys.path.append('/opt/spark-apps')
```

## Copy-and-run local script

```bash
docker cp scripts/your_script.py portfolio-spark:/tmp/your_script.py
docker exec portfolio-spark python3 /tmp/your_script.py
```

## Lead takeaway

Report: failing layer (MinIO / catalog DDL / JDBC / Spark job), exact error snippet, and the one command that validated the fix.
