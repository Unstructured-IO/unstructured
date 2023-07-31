import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url


def azure(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    account_name: Optional[str],
    account_key: Optional[str],
    connection_string: Optional[str],
    remote_url: str,
    recursive: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    if not account_name and not connection_string:
        raise ValueError(
            "missing either account-name or connection-string",
        )

    connector_config.download_dir = update_download_dir_remote_url(
        connector_config=connector_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.azure import (
        AzureBlobStorageConnector,
        SimpleAzureBlobStorageConfig,
    )

    if account_name:
        access_kwargs = {
            "account_name": account_name,
            "account_key": account_key,
        }
    elif connection_string:
        access_kwargs = {"connection_string": connection_string}
    else:
        access_kwargs = {}
    doc_connector = AzureBlobStorageConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleAzureBlobStorageConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs=access_kwargs,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
