import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def airtable(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    personal_access_token: str,
    list_of_paths: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        personal_access_token.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.airtable import (
        AirtableConnector,
        SimpleAirtableConfig,
    )

    doc_connector = AirtableConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleAirtableConfig(
            personal_access_token=personal_access_token,
            list_of_paths=list_of_paths,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
