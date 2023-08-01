import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def gdrive(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    service_account_key: str,
    recursive: bool,
    drive_id: str,
    extension: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        drive_id.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.google_drive import (
        GoogleDriveConnector,
        SimpleGoogleDriveConfig,
    )

    doc_connector = GoogleDriveConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleGoogleDriveConfig(
            drive_id=drive_id,
            service_account_key=service_account_key,
            recursive=recursive,
            extension=extension,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
