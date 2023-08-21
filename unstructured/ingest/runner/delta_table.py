import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from unstructured.ingest.interfaces import ProcessorConfigs, StandardConnectorConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash


def delta_table(
    verbose: bool,
    connector_config: StandardConnectorConfig,
    processor_config: ProcessorConfigs,
    table_uri: Union[str, Path],
    version: Optional[int] = None,
    storage_options: Optional[Dict[str, str]] = None,
    without_files: bool = False,
    columns: Optional[List[str]] = None,
    **kwargs,
):
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        str(table_uri).encode("utf-8"),
    )
    connector_config.download_dir = update_download_dir_hash(
        connector_name="delta_table",
        connector_config=connector_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.delta_table import (
        DeltaTableConnector,
        SimpleDeltaTableConfig,
    )

    doc_connector = DeltaTableConnector(
        standard_config=connector_config,
        config=SimpleDeltaTableConfig(
            verbose=verbose,
            table_uri=table_uri,
            version=version,
            storage_options=storage_options,
            without_files=without_files,
            columns=columns,
        ),
    )

    process_documents(doc_connector=doc_connector, processor_config=processor_config)
