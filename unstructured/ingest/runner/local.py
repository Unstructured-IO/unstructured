import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.writers import writer_map


def local(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    input_path: str,
    recursive: bool,
    file_glob: t.Optional[str],
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    from unstructured.ingest.connector.local import (
        LocalSourceConnector,
        SimpleLocalConfig,
    )

    source_doc_connector = LocalSourceConnector(  # type: ignore
        connector_config=SimpleLocalConfig(
            input_path=input_path,
            recursive=recursive,
            file_glob=file_glob,
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
