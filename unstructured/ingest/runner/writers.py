import typing as t
from pathlib import Path

from unstructured.ingest.interfaces import BaseDestinationConnector
from unstructured.utils import requires_dependencies


@requires_dependencies(["s3fs", "fsspec"], extras="s3")
def s3_writer(
    remote_url: str,
    anonymous: bool,
    verbose: bool = False,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig
    from unstructured.ingest.connector.s3 import (
        S3DestinationConnector,
        SimpleS3Config,
    )

    return S3DestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleS3Config(
            path=remote_url,
            access_kwargs={"anon": anonymous},
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


@requires_dependencies(["dropboxdrivefs", "fsspec"], extras="dropbox")
def dropbox_writer(
    remote_url: str,
    token: t.Optional[str],
    verbose: bool = False,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.dropbox import (
        DropboxDestinationConnector,
        SimpleDropboxConfig,
    )
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig

    return DropboxDestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleDropboxConfig(
            path=remote_url,
            access_kwargs={"token": token},
        ),
    )


@requires_dependencies(["boxfs", "fsspec"], extras="box")
def box_writer(
    remote_url: str,
    box_app_config: t.Optional[str],
    verbose: bool = False,
) -> BaseDestinationConnector:
    import boxsdk

    from unstructured.ingest.connector.box import (
        BoxDestinationConnector,
        SimpleBoxConfig,
    )
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig

    access_kwargs: t.Dict[str, t.Any] = {"box_app_config": box_app_config}
    if verbose:
        access_kwargs["client_type"] = boxsdk.LoggingClient
    return BoxDestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleBoxConfig(
            path=remote_url,
            access_kwargs=access_kwargs,
        ),
    )


@requires_dependencies(["adlfs", "fsspec"], extras="azure")
def azure_writer(
    remote_url: str,
    account_name: t.Optional[str],
    account_key: t.Optional[str],
    connection_string: t.Optional[str],
    overwrite: bool = False,
    verbose: bool = False,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.azure import (
        AzureBlobStorageDestinationConnector,
        SimpleAzureBlobStorageConfig,
    )
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig

    if account_name:
        access_kwargs = {
            "account_name": account_name,
            "account_key": account_key,
        }
    elif connection_string:
        access_kwargs = {"connection_string": connection_string}
    else:
        access_kwargs = {}

    return AzureBlobStorageDestinationConnector(
        write_config=FsspecWriteConfig(put_kwargs={"overwrite": overwrite}),
        connector_config=SimpleAzureBlobStorageConfig(
            path=remote_url,
            access_kwargs=access_kwargs,
        ),
    )


writer_map: t.Dict[str, t.Callable] = {
    "s3": s3_writer,
    "delta_table": delta_table_writer,
    "box": box_writer,
    "dropbox": dropbox_writer,
    "azure": azure_writer,
}
