import hashlib
import logging
import typing as t
from pathlib import Path

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def delta_table(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    table_uri: t.Union[str, Path],
    version: t.Optional[int] = None,
    storage_options: t.Optional[str] = None,
    without_files: bool = False,
    columns: t.Optional[t.List[str]] = None,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        str(table_uri).encode("utf-8"),
    )
    read_config.download_dir = update_download_dir_hash(
        connector_name="delta_table",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.delta_table import (
        DeltaTableSourceConnector,
        SimpleDeltaTableConfig,
    )

    source_doc_connector = DeltaTableSourceConnector(
        connector_config=SimpleDeltaTableConfig(
            verbose=verbose,
            table_uri=table_uri,
            version=version,
            storage_options=SimpleDeltaTableConfig.storage_options_from_str(storage_options)
            if storage_options
            else None,
            without_files=without_files,
            columns=columns,
        ),
        read_config=read_config,
        partition_config=partition_config,
    )

    dest_doc_connector = None
    if writer_type:
        writer = writer_map[writer_type]
        dest_doc_connector = writer(**writer_kwargs)

    process_documents(
        source_doc_connector=source_doc_connector,
        partition_config=partition_config,
        verbose=verbose,
        dest_doc_connector=dest_doc_connector,
    )
