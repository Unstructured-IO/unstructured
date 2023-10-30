import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector


def azure_writer(
    remote_url: str,
    account_name: t.Optional[str] = None,
    account_key: t.Optional[str] = None,
    connection_string: t.Optional[str] = None,
    overwrite: bool = False,
    verbose: bool = False,
    **kwargs,
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
        write_config=FsspecWriteConfig(write_text_kwargs={"overwrite": overwrite}),
        connector_config=SimpleAzureBlobStorageConfig(
            remote_url=remote_url,
            access_kwargs=access_kwargs,
        ),
    )
