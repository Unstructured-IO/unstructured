#!/usr/bin/env python3

import click
import singlestoredb as s2
from singlestoredb.connection import Connection


def get_connection(
    host: str = None, port: int = None, database: str = None, user: str = None, password: str = None
) -> Connection:
    conn = s2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )
    return conn


def validate(table_name: str, conn: Connection, num_elements: int):
    with conn.cursor() as cur:
        stmt = f"select * from {table_name}"
        count = cur.execute(stmt)
        assert (
            count == num_elements
        ), f"found count ({count}) doesn't match expected value: {num_elements}"
    print("validation successful")


@click.command()
@click.option("--host", type=str, default="localhost", show_default=True)
@click.option("--port", type=int, default=3306, show_default=True)
@click.option("--user", type=str, default="root", show_default=True)
@click.option("--password", type=str, default="password")
@click.option("--database", type=str, required=True)
@click.option("--table-name", type=str, required=True)
@click.option(
    "--num-elements", type=int, required=True, help="The expected number of elements to exist"
)
def run_validation(
    host: str,
    port: int,
    user: str,
    database: str,
    password: str,
    table_name: str,
    num_elements: int,
):
    print(f"Validating that table {table_name} in database {database} has {num_elements} entries")
    conn = get_connection(host=host, port=port, database=database, user=user, password=password)
    validate(table_name=table_name, conn=conn, num_elements=num_elements)


if __name__ == "__main__":
    run_validation()
