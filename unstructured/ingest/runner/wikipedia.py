import hashlib
import logging

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def wikipedia(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    page_title: str,
    auto_suggest: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        page_title.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.wikipedia import (
        SimpleWikipediaConfig,
        WikipediaConnector,
    )

    doc_connector = WikipediaConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleWikipediaConfig(
            title=page_title,
            auto_suggest=auto_suggest,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
