import database.DatabaseConnection as DatabaseConnection
from pathlib import Path

class DatabaseExecutor:

    def __init__(self, db_connection: DatabaseConnection):
        self.db_connection = db_connection

    def execute(self, query: str, params=None):
        conn = self.db_connection.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()

    def executemany(self, query: str, records: list):
        conn = self.db_connection.connect()
        with conn.cursor() as cur:
            cur.executemany(query, records)
        conn.commit()

    def fetchall(self, query: str, params=None):
        conn = self.db_connection.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def fetchone(self, query: str, params=None):
        conn = self.db_connection.connect()
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()