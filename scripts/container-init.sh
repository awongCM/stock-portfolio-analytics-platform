#!/bin/bash
# Container initialization script that runs inside Spark container
# This script starts Spark, initializes Iceberg, and starts Jupyter

set -e

echo "========================================"
echo "Starting Portfolio Analytics Platform"
echo "========================================"

# Start Spark Master
echo "Starting Spark Master..."
/opt/spark/sbin/start-master.sh

# Wait a moment for Spark to start
sleep 3

# Initialize Iceberg tables in background
echo "Initializing Iceberg tables..."
python3 /opt/spark-apps/scripts/init-iceberg.py &

# Start Jupyter Lab (foreground process)
echo "Starting Jupyter Lab on http://localhost:8888"
jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --notebook-dir=/opt/spark-apps \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    --ServerApp.terminado_settings='{"shell_command":["/bin/bash"]}'
