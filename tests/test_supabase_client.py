"""Unit tests for Supabase client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.utils.supabase_client import SupabaseConnection, SupabaseRepository


class TestSupabaseConnection:
    """Test suite for SupabaseConnection."""
    
    @patch.dict('os.environ', {
        'SUPABASE_URL': 'http://test:54321',
        'SUPABASE_KEY': 'test-key',
        'POSTGRES_HOST': 'testhost',
        'POSTGRES_PORT': '5432',
        'POSTGRES_DB': 'testdb',
        'POSTGRES_USER': 'testuser',
        'POSTGRES_PASSWORD': 'testpass'
    })
    def test_initialization(self):
        """Test SupabaseConnection initialization."""
        conn = SupabaseConnection()
        
        assert conn.url == 'http://test:54321'
        assert conn.key == 'test-key'
    
    @patch('src.utils.supabase_client.create_client')
    def test_get_client(self, mock_create_client):
        """Test getting Supabase client."""
        mock_client = Mock()
        mock_create_client.return_value = mock_client
        
        conn = SupabaseConnection()
        client = conn.get_client()
        
        assert client == mock_client
        mock_create_client.assert_called_once()


class TestSupabaseRepository:
    """Test suite for SupabaseRepository."""
    
    @pytest.fixture
    def mock_client(self):
        """Create a mock Supabase client."""
        mock = MagicMock()
        return mock
    
    @pytest.fixture
    def repository(self, mock_client):
        """Create a SupabaseRepository instance."""
        with patch('src.utils.supabase_client.SupabaseConnection') as mock_conn:
            mock_conn.return_value.get_client.return_value = mock_client
            return SupabaseRepository("test_table")
    
    def test_select_all(self, repository, mock_client):
        """Test select all records."""
        mock_response = Mock()
        mock_response.data = [{"id": "1", "name": "Test"}]
        
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response
        
        result = repository.select_all()
        
        assert len(result) == 1
        assert result[0]["name"] == "Test"
    
    def test_insert(self, repository, mock_client):
        """Test insert record."""
        mock_response = Mock()
        mock_response.data = [{"id": "1", "name": "New Item"}]
        
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response
        
        data = {"name": "New Item"}
        result = repository.insert(data)
        
        assert result["id"] == "1"
        assert result["name"] == "New Item"
