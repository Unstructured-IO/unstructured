import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def outlook(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    user_email: str,
    client_id: Optional[str],
    client_cred: Optional[str],
    tenant: Optional[str],
    authority_url: Optional[str],
    outlook_folders: Optional[str],
    recursive: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(user_email.encode("utf-8"))
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.outlook import (
        OutlookConnector,
        SimpleOutlookConfig,
    )

    doc_connector = OutlookConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleOutlookConfig(
            client_id=client_id,
            client_credential=client_cred,
            user_email=user_email,
            tenant=tenant,
            authority_url=authority_url,
            ms_outlook_folders=SimpleOutlookConfig.parse_folders(outlook_folders)
            if outlook_folders
            else [],
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
