import hashlib
import logging

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def sharepoint(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    site: str,
    client_id: str,
    client_cred: str,
    files_only: bool,
    path: str,
    recursive: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        f"{site}_{path}".encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.sharepoint import (
        SharepointConnector,
        SimpleSharepointConfig,
    )

    doc_connector = SharepointConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleSharepointConfig(
            client_id=client_id,
            client_credential=client_cred,
            site_url=site,
            path=path,
            process_pages=(not files_only),
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
