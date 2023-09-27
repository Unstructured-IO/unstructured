import hashlib
import logging
import typing as t
from uuid import UUID

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def notion(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    api_key: str,
    recursive: bool,
    page_ids: t.Optional[t.List[str]] = None,
    database_ids: t.Optional[t.List[str]] = None,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    page_ids = [str(UUID(p.strip())) for p in page_ids] if page_ids else []
    database_ids = [str(UUID(d.strip())) for d in database_ids] if database_ids else []
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    if not page_ids and not database_ids:
        raise ValueError("no page ids nor database ids provided")

    if page_ids and database_ids:
        hashed_dir_name = hashlib.sha256(
            "{},{}".format(",".join(page_ids), ",".join(database_ids)).encode("utf-8"),
        )
    elif page_ids:
        hashed_dir_name = hashlib.sha256(
            ",".join(page_ids).encode("utf-8"),
        )
    elif database_ids:
        hashed_dir_name = hashlib.sha256(
            ",".join(database_ids).encode("utf-8"),
        )
    else:
        raise ValueError("could not create local cache directory name")

    read_config.download_dir = update_download_dir_hash(
        connector_name="notion",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.notion.connector import (
        NotionSourceConnector,
        SimpleNotionConfig,
    )

    source_doc_connector = NotionSourceConnector(  # type: ignore
        connector_config=SimpleNotionConfig(
            page_ids=page_ids,
            database_ids=database_ids,
            api_key=api_key,
            verbose=verbose,
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
