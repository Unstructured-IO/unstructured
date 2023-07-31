import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def confluence(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    url: str,
    user_email: str,
    api_token: str,
    list_of_spaces: Optional[str],
    max_num_of_spaces: int,
    max_num_of_docs_from_each_space: int,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        url.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.confluence import (
        ConfluenceConnector,
        SimpleConfluenceConfig,
    )

    doc_connector = ConfluenceConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleConfluenceConfig(
            url=url,
            user_email=user_email,
            api_token=api_token,
            list_of_spaces=list_of_spaces,
            max_number_of_spaces=max_num_of_spaces,
            max_number_of_docs_from_each_space=max_num_of_docs_from_each_space,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
