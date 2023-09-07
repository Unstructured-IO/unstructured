import hashlib
import logging
import typing as t

from unstructured.ingest.interfaces import PartitionConfig, ReadConfig
from unstructured.ingest.logger import ingest_log_streaming_init, logger
from unstructured.ingest.processor import process_documents
from unstructured.ingest.runner.utils import update_download_dir_hash
from unstructured.ingest.runner.writers import writer_map


def confluence(
    verbose: bool,
    read_config: ReadConfig,
    partition_config: PartitionConfig,
    url: str,
    user_email: str,
    api_token: str,
    max_num_of_spaces: int,
    max_num_of_docs_from_each_space: int,
    spaces: t.Optional[t.List[str]] = None,
    writer_type: t.Optional[str] = None,
    writer_kwargs: t.Optional[dict] = None,
    **kwargs,
):
    spaces = spaces if spaces else []
    writer_kwargs = writer_kwargs if writer_kwargs else {}

    ingest_log_streaming_init(logging.DEBUG if verbose else logging.INFO)

    hashed_dir_name = hashlib.sha256(
        url.encode("utf-8"),
    )

    read_config.download_dir = update_download_dir_hash(
        connector_name="confluence",
        read_config=read_config,
        hashed_dir_name=hashed_dir_name,
        logger=logger,
    )

    from unstructured.ingest.connector.confluence import (
        ConfluenceSourceConnector,
        SimpleConfluenceConfig,
    )

    source_doc_connector = ConfluenceSourceConnector(  # type: ignore
        connector_config=SimpleConfluenceConfig(
            url=url,
            user_email=user_email,
            api_token=api_token,
            spaces=spaces,
            max_number_of_spaces=max_num_of_spaces,
            max_number_of_docs_from_each_space=max_num_of_docs_from_each_space,
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
