import typing as t
from pathlib import Path

from unstructured.ingest.interfaces import WriteConfig
from unstructured.utils import requires_dependencies


@requires_dependencies(["s3fs", "fsspec"], extras="s3")
def s3_writer(
    remote_url: str,
    anonymous: bool,
    verbose: bool = False,
    **kwargs,
):
    from unstructured.ingest.connector.s3 import (
        S3DestinationConnector,
        SimpleS3Config,
    )

    return S3DestinationConnector(
        write_config=WriteConfig(),
        connector_config=SimpleS3Config(
            path=remote_url,
            access_kwargs={"anon": anonymous},
        ),
    )


@requires_dependencies(["azure"], extras="azure-cognitive-search")
def azure_cognitive_search_writer(
    endpoint: str,
    key: str,
    index: str,
    **kwargs,
):
    from unstructured.ingest.connector.azure_cognitive_search import (
        AzureCognitiveSearchDestinationConnector,
        AzureCognitiveSearchWriteConfig,
        SimpleAzureCognitiveSearchStorageConfig,
    )

    return AzureCognitiveSearchDestinationConnector(
        write_config=AzureCognitiveSearchWriteConfig(
            index=index,
        ),
        connector_config=SimpleAzureCognitiveSearchStorageConfig(
            endpoint=endpoint,
            key=key,
        ),
    )


@requires_dependencies(["deltalake"], extras="delta-table")
def delta_table_writer(
    table_uri: t.Union[str, Path],
    write_column: str,
    mode: t.Literal["error", "append", "overwrite", "ignore"] = "error",
    verbose: bool = False,
    **kwargs,
):
    from unstructured.ingest.connector.delta_table import (
        DeltaTableDestinationConnector,
        DeltaTableWriteConfig,
        SimpleDeltaTableConfig,
    )

    return DeltaTableDestinationConnector(
        write_config=DeltaTableWriteConfig(write_column=write_column, mode=mode),
        connector_config=SimpleDeltaTableConfig(
            table_uri=table_uri,
            verbose=verbose,
        ),
    )


writer_map: t.Dict[str, t.Callable] = {
    "s3": s3_writer,
    "delta_table": delta_table_writer,
    "azure_cognitive_search": azure_cognitive_search_writer,
}
