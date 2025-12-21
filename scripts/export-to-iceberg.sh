#!/bin/bash
# Export data from Supabase to Iceberg

set -e

echo "Exporting data from Supabase to Iceberg..."

docker-compose exec spark spark-submit \
  --master local[*] \
  --packages org.postgresql:postgresql:42.6.0 \
  /opt/spark-apps/scripts/export_to_iceberg.py

echo "Export complete!"
