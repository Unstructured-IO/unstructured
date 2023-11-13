import typing as t


def sql_writer(
    drivername: t.Optional[str],
    username: t.Optional[str],
    password: t.Optional[str],
    host: t.Optional[str],
    database: t.Optional[str],
    port: t.Optional[int],
    table_name_mapping: t.Dict[str, str],
    database_url: t.Optional[str],
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error",
    **kwargs,
):
    from unstructured.ingest.connector.sql.connector import (
        SimpleSqlConfig,
        SqlDestinationConnector,
        SqlWriteConfig,
    )

    return SqlDestinationConnector(
        write_config=SqlWriteConfig(mode=mode, table_name_mapping=table_name_mapping),
        connector_config=SimpleSqlConfig(
            drivername=drivername,
            username=username,
            password=password,
            host=host,
            database=database,
            port=port,
            database_url=database_url,
        ),
    )
