import click
from deltalake import DeltaTable


@click.command()
@click.option("--table-uri", type=str)
def run_check(table_uri):
    print(f"Checking contents of table at {table_uri}")
    delta_table = DeltaTable(
        table_uri=table_uri,
    )

    assert len(delta_table.to_pandas()) == 10
    print("table check complete")


if __name__ == "__main__":
    run_check()
