import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url


def dropbox(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    remote_url: str,
    recursive: bool,
    token: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    connector_config.download_dir = update_download_dir_remote_url(
        connector_config=connector_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.dropbox import (
        DropboxConnector,
        SimpleDropboxConfig,
    )

    doc_connector = DropboxConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleDropboxConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"token": token},
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
