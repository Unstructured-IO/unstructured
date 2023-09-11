import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def onedrive(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    tenant: str,
    user_pname: str,
    client_id: str,
    client_cred: str,
    authority_url: t.Optional[str],
    path: t.Optional[str],
    recursive: bool,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        f"{tenant}_{user_pname}".encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="onedrive",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.onedrive import (
        OneDriveSourceConnector,
        SimpleOneDriveConfig,
    )

    source_doc_connector = OneDriveSourceConnector(  # type: ignore
        connector_config=SimpleOneDriveConfig(
            client_id=client_id,
            client_credential=client_cred,
            user_pname=user_pname,
            tenant=tenant,
            authority_url=authority_url,
            path=path,
            recursive=recursive,
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
