"""Apache Iceberg catalog configuration and initialization."""

from typing import Dict, Any
from pyiceberg.catalog import load_catalog
from pyspark.sql import SparkSession
import os


class IcebergCatalog:
    """Manages Apache Iceberg catalog configuration."""
    
    def __init__(self, catalog_name: str = "portfolio_catalog"):
        self.catalog_name = catalog_name
        self.warehouse_path = os.getenv("ICEBERG_WAREHOUSE", "s3a://iceberg-warehouse/")
        self._catalog = None
    
    def get_catalog_config(self) -> Dict[str, Any]:
        """Get Iceberg catalog configuration."""
        return {
            "type": "hadoop",
            "uri": self.warehouse_path,
            "s3.endpoint": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
            "s3.access-key-id": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "s3.secret-access-key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            "s3.path-style-access": "true",
            "warehouse": self.warehouse_path,
        }
    
    def initialize_catalog(self):
        """Initialize PyIceberg catalog."""
        if not self._catalog:
            self._catalog = load_catalog(
                self.catalog_name,
                **self.get_catalog_config()
            )
        return self._catalog
    
    def get_spark_session(self) -> SparkSession:
        """Create Spark session configured for Iceberg."""
        builder = (
            SparkSession.builder
            .appName("Portfolio-Iceberg")
            .config("spark.sql.extensions", 
                   "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
            .config(f"spark.sql.catalog.{self.catalog_name}", 
                   "org.apache.iceberg.spark.SparkCatalog")
            .config(f"spark.sql.catalog.{self.catalog_name}.type", "hadoop")
            .config(f"spark.sql.catalog.{self.catalog_name}.warehouse", 
                   self.warehouse_path)
            .config("spark.hadoop.fs.s3a.endpoint", 
                   os.getenv("MINIO_ENDPOINT", "http://minio:9000"))
            .config("spark.hadoop.fs.s3a.access.key", 
                   os.getenv("MINIO_ACCESS_KEY", "minioadmin"))
            .config("spark.hadoop.fs.s3a.secret.key", 
                   os.getenv("MINIO_SECRET_KEY", "minioadmin"))
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.impl", 
                   "org.apache.hadoop.fs.s3a.S3AFileSystem")
        )
        
        return builder.getOrCreate()
    
    def create_namespace(self, namespace: str) -> None:
        """Create Iceberg namespace if it doesn't exist."""
        catalog = self.initialize_catalog()
        try:
            catalog.create_namespace(namespace)
            print(f"Created namespace: {namespace}")
        except Exception as e:
            print(f"Namespace {namespace} may already exist: {e}")
    
    def list_tables(self, namespace: str) -> list:
        """List all tables in a namespace."""
        catalog = self.initialize_catalog()
        return catalog.list_tables(namespace)
