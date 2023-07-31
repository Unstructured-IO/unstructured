import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def biomed(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    path: Optional[str],
    api_id: Optional[str],
    api_from: Optional[str],
    api_until: Optional[str],
    max_retries: int,
    max_request_time: int,
    decay: float,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    base_path = (
        path
        if path
        else "{}-{}-{}".format(
            api_id if api_id else "",
            api_from if api_from else "",
            api_until if api_until else "",
        )
    )

    hashed_dir_name = hashlib.sha256(
        base_path.encode("utf-8"),
    )

    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.biomed import (
        BiomedConnector,
        SimpleBiomedConfig,
    )

    doc_connector = BiomedConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleBiomedConfig(
            path=path,
            id_=api_id,
            from_=api_from,
            until=api_until,
            max_retries=max_retries,
            request_timeout=max_request_time,
            decay=decay,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
