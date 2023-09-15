from deltalake import DeltaTable


def run_check():
    delta_table = DeltaTable(
        table_uri="/tmp/delta-table-dest",
    )

    assert len(delta_table.to_pandas()) == 10


if __name__ == "__main__":
    run_check()
