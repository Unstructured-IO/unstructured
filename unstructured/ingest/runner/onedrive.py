import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def onedrive(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    tenant: str,
    user_pname: str,
    client_id: str,
    client_cred: str,
    authority_url: Optional[str],
    path: Optional[str],
    recursive: bool,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        f"{tenant}_{user_pname}".encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.onedrive import (
        OneDriveConnector,
        SimpleOneDriveConfig,
    )

    doc_connector = OneDriveConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleOneDriveConfig(
            client_id=client_id,
            client_credential=client_cred,
            user_pname=user_pname,
            tenant=tenant,
            authority_url=authority_url,
            path=path,
            recursive=recursive,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
