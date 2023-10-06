import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces2 import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor2 import process_documents
from unstructured.ingest.runner.utils2 import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def salesforce(
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    processor_config: ProcessorConfig,
    username: str,
    consumer_key: str,
    private_key_path: str,
    categories: t.List[str],
    verbose: bool = False,
    recursive: bool = False,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(username.encode("utf-8"))

    read_config.download_dir = update_download_dir_hash(
        connector_name="salesforce",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.salesforce import (
        SalesforceSourceConnector,
        SimpleSalesforceConfig,
    )

    source_doc_connector = SalesforceSourceConnector(  # type: ignore
        connector_config=SimpleSalesforceConfig(
            categories=categories,
            username=username,
            consumer_key=consumer_key,
            private_key_path=private_key_path,
            recursive=recursive,
        ),
        read_config=read_config,
        processor_config=processor_config,
    )

    dest_doc_connector = None
    if writer_type:
        writer = writer_map[writer_type]
        dest_doc_connector = writer(**writer_kwargs)

    process_documents(
        source_doc_connector=source_doc_connector,
        partition_config=partition_config,
        dest_doc_connector=dest_doc_connector,
        processor_config=processor_config,
    )
