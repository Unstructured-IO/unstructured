#!/usr/bin/env python3

import os

from sqlalchemy import URL, create_engine, text

DB_USERNAME = os.getenv("DB_USERNAME", "unstructured")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_HOST", 5432)
DB_DATABASE = os.getenv("DB_DATABASE", "elements")
N_ELEMENTS = 605
db_url = URL.create(
    drivername="postgresql",
    username=DB_USERNAME,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_DATABASE,
)

engine = create_engine(db_url)
with engine.connect() as conn:
    count = conn.execute(text("select count(*) from elements;")).scalar()
    try:
        assert count == N_ELEMENTS
    except AssertionError:
        print(f"sql dest check failed: got {count}, expected {N_ELEMENTS}")
        raise

    print("sql dest check success")
