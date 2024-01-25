import sqlite3
import sys
from pathlib import Path

if __name__ == "__main__":
    connection = sqlite3.connect(database=sys.argv[1])

    query = None
    script_path = (Path(__file__).parent / Path("create-sqlite-schema.sql")).resolve()
    with open(script_path) as f:
        query = f.read()
    cursor = connection.cursor()
    cursor.executescript(query)
    connection.close()
