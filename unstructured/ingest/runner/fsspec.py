import logging
import warnings
from urllib.parse import urlparse

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url


def fsspec(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    remote_url: str,
    recursive: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    connector_config.download_dir = update_download_dir_remote_url(
        connector_config=connector_config,
        remote_url=remote_url,
        logger=logger,
    )

    protocol = urlparse(remote_url).scheme
    warnings.warn(
        f"`fsspec` protocol {protocol} is not directly supported by `unstructured`,"
        " so use it at your own risk. Supported protocols are `gcs`, `gs`, `s3`, `s3a`,"
        "`dropbox`, `abfs` and `az`.",
        UserWarning,
    )

    from unstructured.ingest.connector.fsspec import (
        FsspecConnector,
        SimpleFsspecConfig,
    )

    doc_connector = FsspecConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleFsspecConfig(
            path=remote_url,
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
