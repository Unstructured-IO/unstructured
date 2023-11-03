import typing as t
from pathlib import Path

from unstructured.ingest.interfaces import BaseDestinationConnector


def delta_table_writer(
    table_uri: t.Union[str, Path],
    drop_empty_cols: bool = False,
    overwrite_schema: bool = False,
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error",
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.delta_table import (
        DeltaTableDestinationConnector,
        DeltaTableWriteConfig,
        SimpleDeltaTableConfig,
    )

    return DeltaTableDestinationConnector(
        write_config=DeltaTableWriteConfig(
            mode=mode, drop_empty_cols=drop_empty_cols, overwrite_schema=overwrite_schema
        ),
        connector_config=SimpleDeltaTableConfig(
            table_uri=table_uri,
        ),
    )
