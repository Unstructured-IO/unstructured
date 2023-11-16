#!/usr/bin/env python3

import os
import sys

from sqlalchemy import URL, create_engine, text

DB_USERNAME = os.getenv("DB_USERNAME", "unstructured")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_HOST", 5432)
DB_DATABASE = os.getenv("DB_DATABASE", "elements")
N_ELEMENTS = 5

if __name__ == "__main__":
    database_name = sys.argv[1]
    db_url = URL.create(
        drivername=database_name,
        username=DB_USERNAME,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_DATABASE,
    )
    if database_name == "sqlite":
        db_url = "sqlite:////" + os.getcwd() + "/test_unstructured_ingest/elements.db"

    print(f"Running SQL output test for at {db_url}")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        count = conn.execute(text("select count(*) from elements;")).scalar()
        try:
            assert count == N_ELEMENTS
        except AssertionError:
            print(f"{database_name} dest check failed: got {count}, expected {N_ELEMENTS}")
            raise

        print(f"{database_name} dest check success")
