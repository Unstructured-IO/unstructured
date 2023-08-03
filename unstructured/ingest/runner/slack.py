import hashlib
import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def slack(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    channels: str,
    token: str,
    start_date: Optional[str],
    end_date: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        channels.encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.slack import (
        SimpleSlackConfig,
        SlackConnector,
    )

    doc_connector = SlackConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleSlackConfig(
            channels=SimpleSlackConfig.parse_channels(channels),
            token=token,
            oldest=start_date,
            latest=end_date,
            verbose=verbose,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
