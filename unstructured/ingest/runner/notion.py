import hashlib
import logging

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def notion(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    page_ids: str,
    api_key: str,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        page_ids.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.notion import (
        NotionConnector,
        SimpleNotionConfig,
    )

    doc_connector = NotionConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleNotionConfig(
            page_ids=SimpleNotionConfig.parse_page_ids(page_ids_str=page_ids),
            api_key=api_key,
            logger=logger,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
