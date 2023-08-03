import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def elasticsearch(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    url: str,
    index_name: str,
    jq_query: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        f"{url}_{index_name}".encode(
            "utf-8",
        ),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.elasticsearch import (
        ElasticsearchConnector,
        SimpleElasticsearchConfig,
    )

    doc_connector = ElasticsearchConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleElasticsearchConfig(
            url=url,
            index_name=index_name,
            jq_query=jq_query,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
