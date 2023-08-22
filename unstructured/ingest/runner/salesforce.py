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
    salesforce_categories: str,
    salesforce_username: str,
    salesforce_consumer_key: str,
    salesforce_private_key_path: str,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(salesforce_username.encode("utf-8"))
    connector_config.download_dir = update_download_dir_hash(
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
            salesforce_categories=SimpleSalesforceConfig.parse_folders(salesforce_categories),
            salesforce_username=salesforce_username,
            salesforce_consumer_key=salesforce_consumer_key,
            salesforce_private_key_path=salesforce_private_key_path,
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
