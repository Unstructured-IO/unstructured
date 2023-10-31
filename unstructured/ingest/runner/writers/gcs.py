import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector


def gcs_writer(
    remote_url: str,
    service_account_key: t.Optional[str],
    verbose: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig
    from unstructured.ingest.connector.gcs import (
        GcsDestinationConnector,
        SimpleGcsConfig,
    )

    return GcsDestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleGcsConfig(
            remote_url=remote_url,
            access_kwargs={"token": service_account_key},
        ),
    )
