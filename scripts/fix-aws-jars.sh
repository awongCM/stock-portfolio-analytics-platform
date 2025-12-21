#!/bin/bash
# Fix missing AWS SDK JAR in Spark container

set -e

echo "Fixing AWS SDK dependencies..."

# Download AWS SDK v1 bundle JAR to the container
docker exec portfolio-spark bash -c "
    cd /opt/spark/jars && \
    wget -q https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar && \
    echo '✓ Downloaded aws-java-sdk-bundle-1.12.262.jar'
"

# Verify the JAR exists
docker exec portfolio-spark bash -c "
    if [ -f /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar ]; then
        echo '✓ AWS SDK JAR installed successfully'
        ls -lh /opt/spark/jars/aws-java-sdk-bundle-1.12.262.jar
    else
        echo '✗ Failed to install AWS SDK JAR'
        exit 1
    fi
"

echo ""
echo "====================================================================="
echo "✓ Fix complete! Please restart your Jupyter kernel:"
echo "   1. In Jupyter, click 'Kernel' → 'Restart Kernel'"
echo "   2. Or restart the notebook"
echo "====================================================================="
