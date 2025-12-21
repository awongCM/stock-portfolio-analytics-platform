"""Pytest configuration and fixtures."""

import pytest
import os
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
