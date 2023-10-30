import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector


def dropbox_writer(
    remote_url: str,
    token: t.Optional[str],
    verbose: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.dropbox import (
        DropboxDestinationConnector,
        SimpleDropboxConfig,
    )
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig

    return DropboxDestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleDropboxConfig(
            remote_url=remote_url,
            access_kwargs={"token": token},
        ),
    )
