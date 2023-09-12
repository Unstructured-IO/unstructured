import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_remote_url
from unstructured.ingest.runner.writers import writer_map


def azure(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    account_name: t.Optional[str],
    account_key: t.Optional[str],
    connection_string: t.Optional[str],
    remote_url: str,
    recursive: bool,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}
    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    if not account_name and not connection_string:
        raise ValueError(
            "missing either account-name or connection-string",
        )

    read_config.download_dir = update_download_dir_remote_url(
        connector_name="azure",
        read_config=read_config,
        remote_url=remote_url,
        logger=logger,
    )

    from unstructured.ingest.connector.azure import (
        AzureBlobStorageSourceConnector,
        SimpleAzureBlobStorageConfig,
    )

    if account_name:
        access_kwargs = {
            "account_name": account_name,
            "account_key": account_key,
        }
    elif connection_string:
        access_kwargs = {"connection_string": connection_string}
    else:
        access_kwargs = {}
    source_doc_connector = AzureBlobStorageSourceConnector(  # type: ignore
        connector_config=SimpleAzureBlobStorageConfig(
            path=remote_url,
            recursive=recursive,
            access_kwargs=access_kwargs,
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
