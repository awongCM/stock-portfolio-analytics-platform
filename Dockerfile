# Dockerfile for PySpark with Apache Iceberg and AWS Glue support
FROM python:3.11-slim

USER root

# Install Java 11 (required for Spark)
RUN apt-get update && apt-get install -y \
    openjdk-21-jre-headless \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-arm64
ENV PATH=$PATH:$JAVA_HOME/bin

# Install Spark
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
RUN apt-get update && apt-get install -y wget && \
    wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} /opt/spark && \
    rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz && \
    apt-get clean

ENV SPARK_HOME=/opt/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.10.9.7-src.zip:$PYTHONPATH

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    vim \
    git \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    pyiceberg[s3fs,glue,duckdb]==0.6.0 \
    pandas==2.1.4 \
    numpy==1.26.3 \
    supabase==2.3.4 \
    python-dotenv==1.0.0 \
    boto3==1.34.23 \
    yfinance==0.2.55 \
    sqlalchemy==2.0.25 \
    psycopg2-binary==2.9.9 \
    jupyterlab==4.0.10 \
    matplotlib==3.8.2 \
    seaborn==0.13.1

# Download Iceberg and AWS bundle JARs
RUN mkdir -p /opt/spark/jars && \
    wget -P /opt/spark/jars/ \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar \
    https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.4.3/iceberg-aws-bundle-1.4.3.jar \
    https://repo1.maven.org/maven2/software/amazon/awssdk/bundle/2.20.131/bundle-2.20.131.jar \
    https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar \
    https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar \
    https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.1/postgresql-42.7.1.jar

# Configure Spark for Iceberg
RUN mkdir -p /opt/spark/conf && \
    echo "spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.sql.catalog.iceberg.type=hadoop" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.sql.catalog.iceberg.warehouse=s3a://iceberg-warehouse/" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.hadoop.fs.s3a.endpoint=http://minio:9000" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.hadoop.fs.s3a.access.key=minioadmin" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.hadoop.fs.s3a.secret.key=minioadmin" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.hadoop.fs.s3a.path.style.access=true" >> /opt/spark/conf/spark-defaults.conf && \
    echo "spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem" >> /opt/spark/conf/spark-defaults.conf

# Create working directories
RUN mkdir -p /opt/spark-apps /opt/spark-warehouse

WORKDIR /opt/spark-apps

# Expose ports
EXPOSE 8080 7077 4040 8888

# Create entrypoint script
RUN echo '#!/bin/bash\n\
    $SPARK_HOME/sbin/start-master.sh\n\
    jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token="" --NotebookApp.password=""\n\
    ' > /opt/entrypoint.sh && chmod +x /opt/entrypoint.sh

CMD ["/opt/entrypoint.sh"]
