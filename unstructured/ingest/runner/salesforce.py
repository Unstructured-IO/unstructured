import hashlib
import logging

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def salesforce(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    recursive: bool,
    categories: str,
    username: str,
    consumer_key: str,
    private_key_path: str,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(username.encode("utf-8"))
    connector_config.download_dir = update_download_dir_hash(
        connector_name="salesforce",
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.salesforce import (
        SalesforceConnector,
        SimpleSalesforceConfig,
    )

    doc_connector = SalesforceConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleSalesforceConfig(
            categories=SimpleSalesforceConfig.parse_folders(categories),
            username=username,
            consumer_key=consumer_key,
            private_key_path=private_key_path,
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
