import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def biomed(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    path: t.Optional[str],
    api_id: t.Optional[str],
    api_from: t.Optional[str],
    api_until: t.Optional[str],
    max_retries: int,
    max_request_time: int,
    decay: float,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)
    base_path = (
        path
        if path
        else "{}-{}-{}".format(
            api_id if api_id else "",
            api_from if api_from else "",
            api_until if api_until else "",
        )
    )

    hashed_dir_name = hashlib.sha256(
        base_path.encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="biomed",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.biomed import (
        BiomedSourceConnector,
        SimpleBiomedConfig,
    )

    source_doc_connector = BiomedSourceConnector(  # type: ignore
        connector_config=SimpleBiomedConfig(
            path=path,
            id_=api_id,
            from_=api_from,
            until=api_until,
            max_retries=max_retries,
            request_timeout=max_request_time,
            decay=decay,
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
