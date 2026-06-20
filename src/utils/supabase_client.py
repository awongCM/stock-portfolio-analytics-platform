"""Supabase database connection and utilities."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from supabase import create_client, Client
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Load env from repo root so Spark jobs work regardless of cwd
_repo_root = Path(__file__).resolve().parents[2]
_env_local = _repo_root / ".env.local"
_env = _repo_root / ".env"
if _env_local.exists():
    load_dotenv(_env_local, override=True)
elif _env.exists():
    load_dotenv(_env)
else:
    load_dotenv()


class SupabaseConnection:
    """Manages Supabase client connections."""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        self.key = os.getenv("SUPABASE_KEY", "")
        self.service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        self._client: Optional[Client] = None
    
    def get_client(self, use_service_key: bool = False) -> Client:
        """Get Supabase client instance."""
        if not self._client:
            key = self.service_key if use_service_key else self.key
            self._client = create_client(self.url, key)
        return self._client
    
    def get_postgres_engine(self) -> Engine:
        """Get SQLAlchemy engine for direct PostgreSQL access."""
        # Default to localhost when running from host terminal
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "portfolio")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        return create_engine(connection_string)
    
    def test_connection(self) -> bool:
        """Test the Supabase connection."""
        try:
            client = self.get_client()
            # Try to query a table
            result = client.table("portfolios").select("*").limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


def get_postgres_engine() -> Engine:
    """Helper function to get PostgreSQL engine directly."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "portfolio")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return create_engine(connection_string)


class SupabaseRepository:
    """Base repository class for Supabase operations."""
    
    def __init__(self, table_name: str):
        self.connection = SupabaseConnection()
        self.client = self.connection.get_client()
        self.table_name = table_name
    
    def select_all(self, limit: Optional[int] = None) -> list:
        """Select all records from table."""
        query = self.client.table(self.table_name).select("*")
        if limit:
            query = query.limit(limit)
        response = query.execute()
        return response.data
    
    def select_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Select record by ID."""
        response = self.client.table(self.table_name).select("*").eq("id", id).execute()
        return response.data[0] if response.data else None
    
    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new record."""
        response = self.client.table(self.table_name).insert(data).execute()
        return response.data[0]
    
    def update(self, id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a record by ID."""
        response = self.client.table(self.table_name).update(data).eq("id", id).execute()
        return response.data[0]
    
    def delete(self, id: str) -> None:
        """Delete a record by ID."""
        self.client.table(self.table_name).delete().eq("id", id).execute()
