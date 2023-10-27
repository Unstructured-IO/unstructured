import click
from deltalake import DeltaTable


@click.command()
@click.option("--table-uri", type=str)
def run_check(table_uri):
    print(f"Checking contents of table at {table_uri}")
    delta_table = DeltaTable(
        table_uri=table_uri,
    )

    df = delta_table.to_pandas()
    expected_rows = 5
    expected_columns = 18
    print(f"Number of rows in table vs expected: {len(df)}/{expected_rows}")
    print(f"Number of columns in table vs expected: {len(df.columns)}/{expected_columns}")
    assert len(df) == 5
    assert len(df.columns) == 18
    print("table check complete")


if __name__ == "__main__":
    run_check()
