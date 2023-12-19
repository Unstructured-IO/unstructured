#!/usr/bin/env python3

import sys

N_ELEMENTS = 5


def create_connection(db_type, database=None, port=None):
    if db_type == "postgresql" or db_type == "pgvector":
        from psycopg2 import connect

        return connect(
            user="unstructured",
            password="test",
            dbname="elements",
            host="localhost",
            port=port,
        )
    elif db_type == "sqlite":
        from sqlite3 import connect

        return connect(database=database)
    raise ValueError(f"Unsupported database {db_type} connection.")


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
        query = (
            f"SELECT * FROM elements ORDER BY embeddings <-> '{[0.1 for i in range(384)]}' LIMIT 1;"
        )
        cursor = conn.cursor()
        cursor.execute(query)
        res = cursor.fetchone()
        assert res[2] == "Mallori"
        print("Result of vector search against pgvector with embeddings successful")

    try:
        assert count == N_ELEMENTS
    except AssertionError:
        print(f"{database_name} dest check failed: got {count}, expected {N_ELEMENTS}")
        raise
    finally:
        cursor.close()
        conn.close()

    print(f"SUCCESS: {database_name} dest check")
