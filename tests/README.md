# Tests

This directory contains unit and integration tests for the portfolio analytics platform.

## Running Tests

### Run all tests

```bash
poetry run pytest
```

### Run with coverage

```bash
poetry run pytest --cov=src --cov-report=html
```

### Run specific test file

```bash
poetry run pytest tests/test_supabase_client.py
```

### Run specific test

```bash
poetry run pytest tests/test_analytics.py::TestPortfolioAnalyzer::test_analyzer_initialization
```

## Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_supabase_client.py` - Tests for Supabase connectivity
- `test_analytics.py` - Tests for portfolio analytics
- `test_ingestion.py` - Tests for data ingestion (to be added)
- `test_iceberg.py` - Tests for Iceberg operations (to be added)

## Integration Tests

Integration tests require Docker services to be running:

```bash
./scripts/start-services.sh
poetry run pytest -m integration
```

## Mocking

We use `pytest-mock` for mocking external dependencies like:

- Supabase API calls
- Spark sessions
- File system operations
