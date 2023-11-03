import click
from deltalake import DeltaTable


@click.command()
@click.option("--table-uri", type=str)
def run_check(table_uri):
    print(f"Checking contents of table at {table_uri}")
    delta_table = DeltaTable(
        table_uri=table_uri,
    )

    expected_rows = 5
    found_rows = len(delta_table.to_pandas())
    print(
        f"Checking if expected number of rows ({expected_rows}) "
        f"matches how many were found: {found_rows}"
    )
    assert (
        expected_rows == found_rows
    ), f"expected number of rows doesn't match how many were found: {expected_rows}/{found_rows}"
    print("table check complete")


if __name__ == "__main__":
    run_check()
