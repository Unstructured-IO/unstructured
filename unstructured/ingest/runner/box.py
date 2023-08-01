import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url


def box(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    remote_url: str,
    recursive: bool,
    box_app_config: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    connector_config.download_dir = update_download_dir_remote_url(
        connector_config=connector_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.box import BoxConnector, SimpleBoxConfig

    doc_connector = BoxConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleBoxConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs={"box_app_config": box_app_config},
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
