#!/usr/bin/env python3

import sys

# # none of these are in the environment
# DB_USERNAME = os.getenv("DB_USERNAME", "unstructured")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "test")
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = os.getenv("DB_PORT", 5432)
# DB_DATABASE = os.getenv("DB_DATABASE", "elements")
N_ELEMENTS = 5


def create_connection(db_name, database=None, port=None):
    if db_name == "postgresql" or db_name == "pgvector":
        from psycopg2 import connect

        return connect(
            user="unstructured",
            password="test",
            dbname="elements",
            host="localhost",
            port=port,
        )
    elif db_name == "sqlite":
        from sqlite3 import connect

        return connect(database=database)
    raise ValueError(f"Unsupported database {db_name} connection.")


if __name__ == "__main__":
    database_name = sys.argv[1]
    db_url = None
    port = None
    if database_name == "sqlite":
        db_url = sys.argv[2]
    else: 
        port = sys.argv[2]

    print(f"Running SQL output test for: {database_name}")
    conn = create_connection(database_name, db_url, port)
    query = "select count(*) from elements;"
    cursor = conn.cursor()
    cursor.execute(query)
    count = cursor.fetchone()[0]

    if database_name == "pgvector":
        query = "SELECT AVG(embeddings) FROM elements;"
        cursor = conn.cursor()
        cursor.execute(query)
        res = cursor.fetchone()
        print(f"Result of {query} against pgvector with embeddings")
        print(res)

    try:
        assert count == N_ELEMENTS
    except AssertionError:
        print(f"{database_name} dest check failed: got {count}, expected {N_ELEMENTS}")
        raise
    finally:
        cursor.close()
        conn.close()

    print(f"SUCCESS: {database_name} dest check")
