"""Database connection and execution utilities."""

import os
import psycopg2
import sqlite3
from psycopg2.extras import RealDictCursor
from app.config import settings

class DatabaseConnection:
    """PostgreSQL connection context manager."""
    def __init__(self):
        self.conn_str = f"host={settings.PG_HOST} port={settings.PG_PORT} dbname={settings.PG_DBNAME} user={settings.PG_USER} password={settings.PG_PASSWORD}"
        self.conn = None

    def __enter__(self):
        self.conn = psycopg2.connect(self.conn_str, cursor_factory=RealDictCursor)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

class DatabaseExecutor:
    """Executes CRUD operations on PostgreSQL."""
    @staticmethod
    def execute(query: str, params: tuple = None, commit: bool = False):
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if commit:
                    conn.commit()
                    return None
                if cur.description:
                    return cur.fetchall()
                return None

class SchemaManager:
    """Manages PostgreSQL schema initialization."""
    @staticmethod
    def initialize_schema():
        sql_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sql"))
        if not os.path.exists(sql_dir):
            print(f"SQL directory not found at {sql_dir}")
            return
            
        sql_files = sorted([f for f in os.listdir(sql_dir) if f.endswith(".sql")])
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                for file in sql_files:
                    file_path = os.path.join(sql_dir, file)
                    with open(file_path, "r") as f:
                        cur.execute(f.read())
            conn.commit()

def get_sqlite_connection():
    """Returns a connection to the local SQLite database."""
    return sqlite3.connect(settings.DB_PATH)
