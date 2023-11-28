#!/usr/bin/env python3

import os
import sys

DB_USERNAME = os.getenv("DB_USERNAME", "unstructured")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_HOST", 5432)
DB_DATABASE = os.getenv("DB_DATABASE", "elements")
N_ELEMENTS = 5


def create_connection(db_name, database=None):
    if db_name == "postgresql":
        from psycopg2 import connect

        return connect(
            user=DB_USERNAME,
            password=DB_PASSWORD,
            dbname=DB_DATABASE,
            host=DB_HOST,
            port=DB_PORT,
        )
    elif db_name == "mysql":
        import mysql.connector

        return mysql.connector.connect(
            user=DB_USERNAME,
            password=DB_PASSWORD,
            database=DB_DATABASE,
            host=DB_HOST,
            port=DB_PORT,
        )
    elif db_name == "sqlite":
        from sqlite3 import connect

        return connect(database=database)
    raise ValueError(f"Unsupported database {db_name} connection.")


if __name__ == "__main__":
    database_name = sys.argv[1]
    db_url = None
    if database_name == "sqlite":
        db_url = sys.argv[2]

    print(f"Running SQL output test for: {database_name}")
    conn = create_connection(database_name, db_url)
    query = "select count(*) from elements;"
    cursor = conn.cursor()
    cursor.execute(query)
    count = cursor.fetchone()[0]

    try:
        assert count == N_ELEMENTS
    except AssertionError:
        print(f"{database_name} dest check failed: got {count}, expected {N_ELEMENTS}")
        raise
    print(f"SUCCESS: {database_name} dest check")
