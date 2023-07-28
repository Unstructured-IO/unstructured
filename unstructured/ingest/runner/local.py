import logging
from typing import Optional

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init
from unstructured.ingest.processor import process_documents


def local(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    input_path: str,
    recursive: bool,
    file_glob: Optional[str],
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    from unstructured.ingest.connector.local import (
        LocalConnector,
        SimpleLocalConfig,
    )

    doc_connector = LocalConnector(  # type: ignore
        standard_config=connector_config,
        config=SimpleLocalConfig(
            input_path=input_path,
            recursive=recursive,
            file_glob=file_glob,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
