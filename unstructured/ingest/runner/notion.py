import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def notion(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    api_key: str,
    recursive: bool,
    page_ids: Optional[str] = "",
    database_ids: Optional[str] = "",
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    if not page_ids and not database_ids:
        raise ValueError("no page ids nor database ids provided")

    if page_ids and database_ids:
        hashed_dir_name = hashlib.sha256(
            f"{page_ids},{database_ids}".encode("utf-8"),
        )
    elif page_ids:
        hashed_dir_name = hashlib.sha256(
            page_ids.encode("utf-8"),
        )
    elif database_ids:
        hashed_dir_name = hashlib.sha256(
            database_ids.encode("utf-8"),
        )
    else:
        raise ValueError("could not create local cache directory name")
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.notion.connector import (
        NotionConnector,
        SimpleNotionConfig,
    )

    doc_connector = NotionConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleNotionConfig(
            page_ids=SimpleNotionConfig.parse_ids(ids_str=page_ids) if page_ids else [],
            database_ids=SimpleNotionConfig.parse_ids(ids_str=database_ids) if database_ids else [],
            api_key=api_key,
            verbose=verbose,
            recursive=recursive,
            logger=logger,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
