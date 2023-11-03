import typing as t

from unstructured.utils import requires_dependencies

def sql_writer(
    db_name: str,
    username: str,
    password: str,
    host: str,
    database: str,
    port: int = 5432,
    **kwargs,
):
    from unstructured.ingest.connector.sql import (
        SimpleSqlConfig,
        SqlDestinationConnector,
        SqlWriteConfig,
    )

    return SqlDestinationConnector(
        write_config=SqlWriteConfig(),
        connector_config=SimpleSqlConfig(
            db_name=db_name,
            username=username,
            password=password,
            host=host,
            database=database,
            port=port
        ),
    )
