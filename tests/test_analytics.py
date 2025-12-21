"""Unit tests for portfolio performance analytics."""

import pytest
from unittest.mock import Mock, patch
from src.analytics.portfolio_performance import PortfolioAnalyzer


class TestPortfolioAnalyzer:
    """Test suite for PortfolioAnalyzer."""
    
    @pytest.fixture
    def mock_spark_session(self):
        """Create a mock Spark session."""
        mock_spark = Mock()
        return mock_spark
    
    @pytest.fixture
    def analyzer(self, mock_spark_session):
        """Create a PortfolioAnalyzer instance with mocked dependencies."""
        with patch('src.analytics.portfolio_performance.IcebergCatalog') as mock_catalog:
            mock_catalog.return_value.get_spark_session.return_value = mock_spark_session
            mock_catalog.return_value.catalog_name = "test_catalog"
            
            return PortfolioAnalyzer(portfolio_id="test-portfolio-id")
    
    def test_analyzer_initialization(self, analyzer):
        """Test that analyzer initializes correctly."""
        assert analyzer.portfolio_id == "test-portfolio-id"
        assert analyzer.catalog_name == "test_catalog"
    
    def test_calculate_portfolio_value_empty_holdings(self, analyzer, mock_spark_session):
        """Test portfolio value calculation with no holdings."""
        # Mock empty holdings
        mock_df = Mock()
        mock_df.collect.return_value = []
        
        with patch.object(analyzer, 'calculate_current_holdings', return_value=mock_df):
            result = analyzer.calculate_portfolio_value()
            
            assert result["total_value"] == 0
            assert result["total_cost"] == 0
            assert result["unrealized_gain"] == 0
            assert result["unrealized_gain_pct"] == 0


class TestTechnicalIndicators:
    """Test suite for technical indicators."""
    
    @pytest.fixture
    def indicators(self):
        """Create TechnicalIndicators instance."""
        from src.analytics.technical_indicators import TechnicalIndicators
        
        with patch('src.analytics.technical_indicators.IcebergCatalog'):
            return TechnicalIndicators()
    
    def test_sma_calculation(self, indicators):
        """Test SMA calculation logic."""
        # This would test the SMA calculation with sample data
        pass
    
    def test_rsi_calculation(self, indicators):
        """Test RSI calculation logic."""
        # This would test the RSI calculation with sample data
        pass
