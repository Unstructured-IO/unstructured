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
    number_of_rows = len(df)
    assert number_of_rows == 5, (
        f"number of rows in generated table ({number_of_rows}) "
        f"doesn't match expected value: {expected_rows}"
    )

    """
    The number of columns is associated with the flattened JSON structure of the partition output.
    If this changes, it's most likely due to the metadata changing in the output.
    """
    number_of_columns = len(df.columns)
    assert number_of_columns == 18, (
        f"number of columns in generated table ({number_of_columns}) doesn't "
        f"match expected value: {expected_columns}"
    )
    print("table check complete")


if __name__ == "__main__":
    run_check()
