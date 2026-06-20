"""Pytest configuration and fixtures."""

import os
import sys
from unittest.mock import MagicMock


def _stub_pyspark_if_needed():
    """Stub PySpark on host to avoid JVM/native segfaults during unit tests."""
    if os.getenv("PYSPARK_INTEGRATION") == "1":
        return

    if "pyspark" in sys.modules:
        return

    class _Row:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def __getitem__(self, key):
            return getattr(self, key)

    mock_sql = MagicMock()
    mock_sql.Row = _Row
    mock_functions = MagicMock()
    def _agg_expr(_col):
        expr = MagicMock()
        expr.alias = lambda name: name
        return expr

    mock_functions.lit = lambda x: x
    mock_functions.col = lambda x: x
    mock_functions.sum = _agg_expr
    mock_functions.avg = _agg_expr
    mock_functions.count = _agg_expr
    mock_functions.when = lambda cond, val: MagicMock(otherwise=lambda default: val if cond else default)
    mock_functions.coalesce = lambda *args: args[0]
    mock_functions.first = lambda *args: args[0]
    mock_window = MagicMock()

    for name, mod in [
        ("pyspark", MagicMock()),
        ("pyspark.sql", mock_sql),
        ("pyspark.sql.functions", mock_functions),
        ("pyspark.sql.window", mock_window),
        ("pyspark.sql.types", MagicMock()),
    ]:
        sys.modules.setdefault(name, mod)


_stub_pyspark_if_needed()

import pytest
from dotenv import load_dotenv

# Load test environment variables
load_dotenv('.env.test')


@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "supabase_url": os.getenv("SUPABASE_URL", "http://localhost:54321"),
        "postgres_host": os.getenv("POSTGRES_HOST", "localhost"),
        "postgres_port": os.getenv("POSTGRES_PORT", "5432"),
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    }


@pytest.fixture
def sample_portfolio_id():
    """Sample portfolio ID for testing."""
    return "test-portfolio-123"


@pytest.fixture
def sample_stock_symbols():
    """Sample stock symbols for testing."""
    return ["AAPL", "MSFT", "GOOGL"]
