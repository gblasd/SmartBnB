from pathlib import Path
import os

class SchemaManager:

    def __init__(self, connection):
        self.connection = connection

    def initialize_database(self):
        
        print(os.getcwd())
        os.chdir("..")
        sql_dir = Path("sql")
        with self.connection.cursor() as cur:
            for sql_file in sorted(sql_dir.glob("*.sql")):
                print(f" Running {sql_file.name}")
                with open(sql_file, "r", encoding="utf-8") as f:
                    cur.execute(f.read())
        self.connection.commit() # Context Manager makes this commit