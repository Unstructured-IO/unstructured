import typing as t

from unstructured.ingest.interfaces import BaseDestinationConnector


def s3_writer(
    remote_url: str,
    anonymous: bool,
    endpoint_url: t.Optional[str] = None,
    verbose: bool = False,
    **kwargs,
) -> BaseDestinationConnector:
    from unstructured.ingest.connector.fsspec import FsspecWriteConfig
    from unstructured.ingest.connector.s3 import (
        S3DestinationConnector,
        SimpleS3Config,
    )

    access_kwargs: t.Dict[str, t.Any] = {"anon": anonymous}
    if endpoint_url:
        access_kwargs["endpoint_url"] = endpoint_url

    return S3DestinationConnector(
        write_config=FsspecWriteConfig(),
        connector_config=SimpleS3Config(
            remote_url=remote_url,
            access_kwargs=access_kwargs,
        ),
    )
